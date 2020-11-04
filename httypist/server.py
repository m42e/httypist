import flask
import contextlib
import functools
import tempfile
import os, os.path
import subprocess
import copy
import pathlib
import yaml
import logging
from . import processor, repo

app = flask.Flask(__name__)

available_templates = {}
authentication = {}


def check_auth(func):
    @functools.wraps(func)
    def login_required(*args, **kwargs):
        if len(authentication) == 0:
            flask.g.allowed = ["*"]
        else:
            if not "Authorization" in request.headers:
                abort(401)
            data = request.headers["Authorization"].encode("ascii", "ignore")
            token = str.replace(str(data), "Bearer ", "")
            if token in authentication:
                flask.g.allowed = authentication[token]

        return func(*args, **kwargs)

    return login_required


@app.before_first_request
def setup():
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    app.logger.addHandler(logging.StreamHandler())
    app.logger.setLevel(logging.DEBUG)
    update_repo()


@app.route("/", methods=["POST"])
@check_auth
def call():
    try:
        mainfile = flask.request.values["main"]
    except:
        return "unable to determine name of main file", 400

    if not ("*" in flask.g.allowed or "manual" in flask.g.allowed):
        abort(403)

    tempdir = tempfile.TemporaryDirectory()
    latexfiles = []
    for filename, file in flask.request.files.items():
        p = os.path.join(tempdir.name, file.name)
        file.save(p)
        if file.name == mainfile:
            latexfiles.append(file.name)

    if len(latexfiles) == 0:
        return "no valid file provided", 400

    logname = os.path.join(tempdir.name, "log.txt")
    with open(logname, "wb+") as logfile:
        logfile.write(tempdir.name.encode("utf8"))
        for lfile in latexfiles:
            try:
                for _ in range(1, 4):
                    output = subprocess.run(
                        ["xelatex", "-interaction=batchmode", lfile],
                        cwd=tempdir.name,
                        capture_output=True,
                    )
                    logfile.write(output.stdout)
            except:
                return "Error during processing", 500

    pdf_filename = mainfile.replace(".tex", ".pdf")
    try:
        return flask.send_file(
            os.path.join(tempdir.name, pdf_filename),
            attachment_filename=pdf_filename,
            as_attachment=True,
        )
    except:
        return "No ouput available", 500


def get_all_request_data():
    data = {
        "args": flask.request.args,
        "form": flask.request.form,
        "json": {},
    }
    if flask.request.is_json:
        data["json"] = flask.request.json
    return data


@app.route("/process/<templatename>", methods=["POST"])
@check_auth
def process_template(templatename):
    if not ("*" in flask.g.allowed or templatename in flask.g.allowed):
        abort(403)
    read_templates()
    template = available_templates[templatename]
    data = get_all_request_data()
    app.logger.info(data["json"])
    processor.process_template.delay(template, data)
    return "1"


@app.route("/process", methods=["POST"])
@check_auth
def process_autotemplate():
    app.logger.info("autotemplate")
    read_templates()
    data = get_all_request_data()
    app.logger.info("json: {}".format(data["json"]))
    use_templates = []
    for name, template in available_templates.items():
        app.logger.info(f"check process {name}")
        if "selector" in template["config"]:
            for selector in template["config"]["selector"]:
                use = processor.process_string(f"{{{{ {selector} }}}}", data) == "True"
                app.logger.info(f"check => {use}")
                if use:
                    if not ("*" in flask.g.allowed or name in flask.g.allowed):
                        continue
                    use_templates.append(name)
        else:
            app.logger.info("no selector")
    for template in use_templates:
        process_template(template)
    return "1"


@app.route("/info")
@check_auth
def info():
    know_keys = []
    for key in available_templates:
        if "*" in flask.g.allowed or key in flask.g.allowed:
            know_keys.append(key)
    return ", ".join(know_keys)


@app.route("/update")
def update_repo():
    repo.update()
    read_templates()
    return "1"


def read_templates():
    authentication.clear()
    base = pathlib.PosixPath("repo")
    try:
        baseconfig = yaml.load(open(base / "config.yml"), Loader=yaml.CLoader)
    except FileNotFoundError:
        baseconfig = {}
    if "access" in baseconfig:
        for e in baseconfig["access"]:
            if isinstance(e["templates"], str):
                authentication[e["token"]] = [e["templates"]]
            else:
                authentication[e["token"]] = [].expand(e["templates"])
    try:
        dirs = [x for x in next(os.walk(base))[1] if not x.startswith(".")]
    except (FileNotFoundError, StopIteration):
        dirs = []
        app.logger.warning("no templates found")
    for dir in dirs:
        path = base / dir
        available_templates[dir] = {}
        template = available_templates[dir]
        template["path"] = str(path)
        template["config"] = copy.deepcopy(baseconfig)
        with contextlib.suppress(FileNotFoundError):
            template["config"].update(
                yaml.load(open(path / "config.yml"), Loader=yaml.CLoader)
            )
            if "access" in baseconfig:
                for e in template["config"]["access"]:
                    if isinstance(e["templates"], str):
                        authentication[e["token"]].append(e["templates"])
                    else:
                        authentication[e["token"]].extend(e["templates"])
    app.logger.debug(available_templates)
