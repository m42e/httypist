import jinja2
import shlex
import tempfile
import glob
import zipfile
import pathlib
import requests
import sys
import os
import tempfile
import subprocess
import importlib
import shutil
import pathlib
import logging
import io
from rq import get_current_job


import http.client as http_client
http_client.HTTPConnection.debuglevel = 1

logger = logging.getLogger(__name__)


def get_filename_infos(filename: pathlib.Path):
    return filename.stem, filename.suffixes[-2][1:]


def get_filetype_template_options(filetype, config):
    return config.get("filetypes", {}).get(filetype, {}).get("jinja", {})


def process_string(string, data):
    try:
        env = jinja2.Environment()
        return env.from_string(string).render(**data)
    except:
        return "False"


class Template(object):
    def __init__(self, template, data):
        self.template = template
        self.data = data
        self.logger = logging.getLogger(__name__)
        self.logstream = io.StringIO()
        self.logger.addHandler(logging.StreamHandler(self.logstream))
        self.logger.info("Template created")

    @property
    def name(self):
        return self.template["name"]

    def process(self):
        self.prepare_files()
        self.process_template_files()
        self.post_processing()
        self.pack_result()
        self.do_callbacks()

    def prepare_files(self):
        self.template_path = pathlib.Path(self.template["path"])
        self.separate_file_types()
        self.create_temp_folder()
        self.prepare_auxilary_files()

    def separate_file_types(self):
        self.template_files = []
        self.auxilary_files = []
        root, self.folders, files = next(os.walk(self.template_path))
        self.logger.info(f"Search files in {root}")
        for file in files:
            filepath = self.template_path / file

            if filepath.suffix == ".jinja":
                self.logger.info(f"found template file {filepath}")
                self.template_files.append(filepath)
            else:
                self.auxilary_files.append(filepath)

    def create_temp_folder(self):
        self._tempdir = tempfile.TemporaryDirectory(prefix=self.name)
        self.tempdir = pathlib.Path(self._tempdir.name)
        self.logger.info(
            f"Created Temporary Directory {self.tempdir} {self.tempdir.is_dir()}"
        )

    def prepare_auxilary_files(self):
        for folder in self.folders:
            self.logger.info(f"copy {folder} to {self.tempdir}")
            shutil.copytree(self.template_path / folder, self.tempdir / folder)
        for file in self.auxilary_files:
            self.logger.info(f"copy {file} to {self.tempdir}")
            shutil.copy(file, self.tempdir / file.relative_to(self.template_path))

    def process_template_files(self):
        loader = jinja2.FileSystemLoader(str(self.template_path), followlinks=True)
        for f in self.template_files:
            self.logger.info(f"process {f}")
            fname, ending = get_filename_infos(f)
            options = get_filetype_template_options(ending, self.template["config"])

            # we might have a separate environment config per filetype
            env = jinja2.Environment(loader=loader, **options)
            jinja_template = env.get_template(str(f.relative_to(self.template_path)))
            with open(self.tempdir / fname, "w") as fout:
                fout.write(jinja_template.render(**self.data))

    def post_processing(self):
        if not "post" in self.template["config"]:
            return
        self.logger.info(f"process post step")
        output = "failed before calling process"
        try:
            for f in self.template_files:
                self.logger.info(f"post_processing for {f}")
                _, ending = get_filename_infos(f)
                try:
                    commands = self.template["config"]["post"][ending]["commands"]
                    for name, command in commands.items():
                        self.logger.info("running %s on %s: %s", name, f, command)
                        command_list = list(
                            shlex.shlex(command, punctuation_chars=True)
                        )
                        output = subprocess.run(
                            command_list,
                            cwd=self.tempdir,
                            check=True,
                            capture_output=True,
                        )

                except KeyError:
                    continue
        except:
            logger.exception(output)
        finally:
            logger.info(output)

    # This has been thought to offer the possiblity to run python transformations but I do not think this is a good idea
    # def execute_processing(self):
    #     if not "execute" in template["config"]:
    #         return
    #     logger.info(f"try to execute specified functions")
    #     # add the path of the template to the pythonpath, we try to call some functions from there
    #     original_pythonpath = sys.path
    #     sys.path.append(template["path"])
    #     for execute in template["config"]["execute"]:
    #         logger.info(f"execute {execute}")
    #         module, function = execute.split(":")
    #         importlib.invalidate_caches()
    #         mod = importlib.import_module(module)
    #         importlib.reload(mod)
    #         method_to_call = getattr(mod, function)
    #         result = method_to_call(template, data, logger)
    #         logger.info(f"execute result: {result}")

    #     sys.path = original_pythonpath

    def pack_result(self):
        self.logger.info("Creating result dir")
        self.resultdir = pathlib.Path(tempfile.mkdtemp(prefix="result_"))
        self.logger.warning("Packing all files")
        with zipfile.ZipFile(
            self.resultdir / "temp.zip", "w", compression=zipfile.ZIP_LZMA
        ) as zf:
            for i in glob.iglob(str(self.tempdir / "**/*"), recursive=True):
                path_in_zip = str(pathlib.Path(i).relative_to(self.tempdir))
                zf.write(i, arcname=path_in_zip)
        self.logger.warning("Packing defined result files")
        with zipfile.ZipFile(
            self.resultdir / "result.zip", "w", compression=zipfile.ZIP_LZMA
        ) as zf:
            try:
                for f in self.template["config"]["output"]["files"]:
                    try:
                        file = self.tempdir / f
                        zf.write(file, arcname=f)
                    except FileNotFoundError as e:
                        self.logger.warning(
                            f"Expected output File {f}({file}) not found (%s)", e
                        )
            except KeyError:
                self.logger.warning("not output files specified")

    def do_callbacks(self):
        if "callbacks" not in self.template["config"]:
            return
        self.logger.error("preparing callback")
        try:
            for cbname, cb in self.template["config"]["callbacks"].items():
                self.logger.info(f"processing callback {cbname}")
                loader = jinja2.FileSystemLoader(self.template_path, followlinks=True)
                env = jinja2.Environment(loader=loader)
                self.logger.info(f'template url for callback {cb["template"]}')
                url = env.from_string(cb["template"]).render(**self.data)
                self.logger.info(f"url for callback {url}")
                postfiles = {}
                headers = {"x-httypist-processed": "1"}
                # todo jobid, ect.
                if "headers" in cb:
                    headers.update(cb["headers"])
                self.logger.debug(f"callback headers {headers}")

                try:
                    self.logger.info(cb["data"])
                    for sendfile in cb["data"]:
                        if "binary" not in sendfile or sendfile["binary"]:
                            openbinary = "rb"
                        else:
                            openbinary = "r"

                        postfiles[sendfile["name"]] = open(
                            self.tempdir / sendfile["file"], openbinary
                        )
                except:
                    self.logger.exception("configuration error for callback files")
                if "send_result" in cb and cb["send_result"]:
                    postfiles['result'] = open(
                        self.resultdir / "result.zip", "rb"
                    )
                if "send_temp" in cb and cb["send_temp"]:
                    postfiles['complete'] = open(
                        self.resultdir / "temp.zip", "rb"
                    )
                if len(postfiles) == 0:
                    postfiles = None
                self.logger.info(f"sending files {postfiles}")
                self.logger.info(f"method: {cb['method']}")
                result = requests.request(
                    cb["method"], url, files=postfiles, headers=headers
                )
                self.logger.info(f"callback result {result.status_code}")
                self.logger.info(f"result callback {result.content}")
        except KeyError:
            self.logger.warn("Insufficent Configuration for callback")

    @property
    def log(self):
        return self.logstream.getvalue()


def process_template(template, data):
    """ This function processes a template, using the data provided. """
    t = Template(template, data)
    t.job = get_current_job()
    t.process()

    result = dict(template=template, data=data, result_folder=t.resultdir, log=t.log)

    return result
