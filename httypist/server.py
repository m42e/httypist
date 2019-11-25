import flask
import contextlib
import tempfile
import os, os.path
import subprocess
import copy
import pathlib
import yaml
from . import processor, repo
from pprint import pprint

app = flask.Flask(__name__)

available_templates = {}


@app.route("/", methods=["POST"])
def call():
    if "main" not in flask.request.values:
        return "missing name of main file"
    mainfile = flask.request.values["main"]
    tempdir = tempfile.TemporaryDirectory()
    latexfiles = []
    for filename, file in flask.request.files.items():
        p = os.path.join(tempdir.name, file.name)
        file.save(p)
        if file.name == mainfile:
            latexfiles.append(file.name)

    logname = os.path.join(tempdir.name, "log.txt")
    with open(logname, "wb+") as logfile:
        logfile.write(tempdir.name.encode("utf8"))
        for lfile in latexfiles:
            for _ in range(1, 4):
                output = subprocess.run(
                    ["xelatex", "-interaction=batchmode", lfile],
                    cwd=tempdir.name,
                    capture_output=True,
                )
                logfile.write(output.stdout)

    pdf_filename = mainfile.replace(".tex", ".pdf")
    return flask.send_file(
        os.path.join(tempdir.name, pdf_filename),
        attachment_filename=pdf_filename,
        as_attachment=True,
    )


def get_all_request_data():
    data = {
        "args": flask.request.args,
        "form": flask.request.form,
        "json": {},
    }
    if flask.request.is_json:
        data["json"] = flask.request.json
    return data


@app.route("/process/<templatename>")
def process_template(templatename):
    template = available_templates[templatename]
    data = get_all_request_data()
    processor.process_template.delay(template, data)
    return "1"


@app.route("/process")
def process_autotemplate():
    data = get_all_request_data()
    use_templates = []
    for name, template in available_templates.items():
        if 'selector' in template['config']:
            for selector in template['config']['selector']:
                use = processor.process_string(f'{{{{ {selector} }}}}', data) == 'True'
                if use:
                    use_templates.append(name)
    for template in use_templates:
        process_template(template)
    return '1'



@app.route("/update")
def update_repo():
    repo.update()
    return "1"


def read_templates():
    base = pathlib.PosixPath("repo")
    try:
        baseconfig = yaml.load(open(base / "config.yml"), Loader=yaml.CLoader)
    except FileNotFoundError:
        baseconfig = {}
    dirs = [x for x in next(os.walk(base))[1] if not x.startswith(".")]
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
    pprint(available_templates)


def main():
    repo.update()
    read_templates()
    app.run(debug=True)