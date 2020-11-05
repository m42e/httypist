import jinja2
import requests
import sys
import os
import tempfile
import subprocess
import importlib
import celery
import shutil
from celery.utils.log import get_task_logger
import pathlib
import io

logger = get_task_logger(__name__)

app = celery.Celery(
    "template_processor", broker=os.getenv("REDIS_URL", "redis://localhost")
)


def get_filename_infos(filename: pathlib.Path):
    return filename.stem, filename.suffixes[-2]


def get_filetype_template_options(filetype, config):
    return config.get("filetypes", {}).get(filetype, {}).get("jinja", {})


def process_string(string, data):
    env = jinja2.Environment()
    return env.from_string(string).render(**data)


@app.task
def process_template(template, data):
    """ This function processes a template, using the data provided. """
    logging_content = io.StreamIO()
    sh = logging.StreamHandler(logging_content)
    logger.addHandler(sh)
    root, folders, files = next(os.walk(template["path"]))
    logger.info(f"Search files in {root}")
    templatefiles, otherfiles = [], []

    template_path = pathlib.Path(template['path'])

    logger.info(f"Create Temporary Directory")
    tempdir = tempfile.TemporaryDirectory()

    # copy non-template files to temp directoy
    for file in files:
        filepath = template_path / file
        if filepath.suffix == 'jinja':
            templatefiles.append(filepath)
        else:
            logger.info(f"copy {file} to {tempdir.name}")
            shutil.copy(os.path.join(template["path"], file), tempdir.name)

    # copy folders to the temp directory
    for folder in folders:
        logger.info(f"copy {file} to {tempdir.name}")
        shutil.copytree(
            os.path.join(template["path"], folder), os.path.join(tempdir.name, folder)
        )
        shutil.copytree

    loader = jinja2.FileSystemLoader(template_path, followlinks=True)
    for f in templatefiles:
        logger.info(f"process {f}")
        fname, ending = get_filename_infos(f)
        options = get_filetype_template_options(ending, template["config"])
        # we might have a separate environment config per filetype
        env = jinja2.Environment(loader=loader, **options)
        t = env.get_template(f)
        with open(os.path.join(tempdir.name, fname), "w") as fout:
            fout.write(t.render(**data))

    # do post-generate-processing if any
    if "post" in template["config"]:
        logger.info(f"process post step")
        output = "failed before calling process"
        try:
            for f in templatefiles:
                fname, ending = get_filename_infos(f)
                if ending in template['config']['post']:
                    template_post = template["config"]["post"][ending]
                    for name, command in template_post['commands'].items():
                        logger.info("running %s: %s", name, " ".join(command))
                        output = subprocess.run(
                            command, cwd=tempdir.name, check=True, capture_output=True
                        )
        finally:
            logger.error(output)

    if "execute" in template["config"]:
        logger.info(f"try to execute specified functions")
        # add the path of the template to the pythonpath, we try to call some functions from there
        original_pythonpath = sys.path
        sys.path.append(template["path"])
        for execute in template["config"]["execute"]:
            logger.info(f"execute {execute}")
            module, function = execute.split(":")
            importlib.invalidate_caches()
            mod = importlib.import_module(module)
            importlib.reload(mod)
            method_to_call = getattr(mod, function)
            result = method_to_call(template, data, logger)
            logger.info(f"execute result: {result}")

        sys.path = original_pythonpath

    if "callback" in template["config"]:
        logger.error("preparing callback")
        cb = template["config"]["callback"]
        env = jinja2.Environment(loader=loader)
        logger.info(f'template url for callback {cb["template"]}')
        url = env.from_string(cb["template"]).render(**data)
        logger.info(f"url for callback {url}")
        postfiles = {}
        headers = {"x-httypist-processed": "1"}
        if "headers" in cb:
            headers.update(cb["headers"])
        logger.info(f"callback headers {headers}")
        for sendfile in cb["data"]:
            if sendfile["binary"]:
                openbinary = "rb"
            else:
                openbinary = "r"
            postfiles[sendfile["name"]] = open(
                os.path.join(tempdir.name, sendfile["file"]), openbinary
            )
            result = requests.request(
                cb["method"], url, files=postfiles, headers=headers
            )
            logger.info(f"callback result {result.status_code}")
            logger.info(f"result callback {result.content}")

    if "output" in template["config"]:
        op = template["config"]["output"]
        for file in op["files"]:
            shutil.move(os.path.join(tempdir.name, file), op["outputdir"])
