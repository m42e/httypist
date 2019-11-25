import jinja2
import requests
import os
import tempfile
import subprocess
import celery
import shutil
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

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
    root, _, files = next(os.walk(template["path"]))
    logger.info(f'Search files in {root}')
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
        logger.info(f'process {f}')
        fname, ending = get_filename_infos(f)
        options = get_filetype_template_options(ending, template["config"])
        env = jinja2.Environment(loader=loader, **options)
        t = env.get_template(f)
        with open(os.path.join(tempdir.name, fname), "w") as fout:
            fout.write(t.render(**data))

    if "post" in template["config"]:
        logger.info(f'process post step')
        output = 'failed before calling process'
        try:
            for name, command in template["config"]["post"].items():
                logger.info(" ".join(command))
                output = subprocess.run(
                    command, cwd=tempdir.name, check=True, capture_output=True
                )
        finally:
            logger.error(output)

    if "callback" in template["config"]:
        logger.error('preparing callback')
        cb = template["config"]["callback"]
        env = jinja2.Environment(loader=loader)
        logger.info(f'template url for callback {cb["template"]}')
        url = env.from_string(cb["template"]).render(**data)
        logger.info(f'url for callback {url}')
        postfiles = {}
        for sendfile in cb["data"]:
            if sendfile["binary"]:
                openbinary = "rb"
            else:
                openbinary = "r"
            postfiles[sendfile["name"]] = open(
                os.path.join(tempdir.name, sendfile["file"]), openbinary
            )
        headers = {
            'x-httypist-processed': '1'
        }
        if 'headers' in cb:
            headers.update(cb['headers'])
        logger.info(f'callback headers {headers}')
        result = requests.request(cb["method"], url, files=postfiles, headers=headers)
        logger.info(f'callback result {result.status_code}')
        logger.info(f'result callback {result.content}')
    if "output" in template["config"]:
        op = template["config"]["output"]
        for file in op["files"]:
            shutil.move(os.path.join(tempdir.name, file), op["outputdir"])
