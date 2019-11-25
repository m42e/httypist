import jinja2
import requests
import os
import tempfile
import subprocess
import celery
import shutil

app = celery.Celery(
    "template_processor", broker=os.getenv("REDIS_URL", "redis://localhost")
)


def get_filename_infos(filename):
    fname = filename[:-6]
    ending = fname.rsplit(".", 1)[1]
    return fname, ending


def get_filetype_template_options(filetype, config):
    return config.get("filetypes", {}).get(filetype, {}).get("jinja", {})


def process_string(string, data):
    env = jinja2.Environment()
    return env.from_string(string).render(**data)


@app.task
def process_template(template, data):
    _, _, files = next(os.walk(template["path"]))
    templatefiles, otherfiles = [], []
    for x in files:
        templatefiles.append(x) if x.endswith(".jinja") else otherfiles.append(x)

    tempdir = tempfile.TemporaryDirectory()
    for file in otherfiles:
        shutil.copy(
            os.path.join(template["path"], file), os.path.join(tempdir.name, file)
        )
    loader = jinja2.FileSystemLoader(template["path"], followlinks=True)
    for f in templatefiles:
        fname, ending = get_filename_infos(f)
        options = get_filetype_template_options(ending, template["config"])
        env = jinja2.Environment(loader=loader, **options)
        t = env.get_template(f)
        with open(os.path.join(tempdir.name, fname), "w") as fout:
            fout.write(t.render(**data))

    if "post" in template["config"]:
        try:
            for name, command in template["config"]["post"].items():
                print(" ".join(command))
                output = subprocess.run(
                    command, cwd=tempdir.name, check=True, capture_output=True
                )
        finally:
            print(open(os.path.join(tempdir.name, "demo2.log")).read())
            print(open(os.path.join(tempdir.name, "demo2.tex")).read())
            print(output)

    if "callback" in template["config"]:
        cb = template["config"]["callback"]
        env = jinja2.Environment(loader=loader)
        url = env.from_string(cb["template"]).render(**data)
        postfiles = {}
        for sendfile in cb["data"]:
            if sendfile["binary"]:
                openbinary = "rb"
            else:
                openbinary = "r"
            postfiles[sendfile["name"]] = open(
                os.path.join(tempdir.name, sendfile["name"]), openbinary
            )
        requests.request(cb["method"], url, files=postfiles)
    if "output" in template["config"]:
        op = template["config"]["output"]
        for file in op["files"]:
            shutil.move(os.path.join(tempdir.name, file), op["outputdir"])
