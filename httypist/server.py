import fastapi
from fastapi.responses import FileResponse, PlainTextResponse
import datetime
import copy
import contextlib
import functools
import os
import yaml
import pathlib
import collections
from rq import Queue
from redis import Redis
from httypist import schema
from . import repo
from . import processor
import logging
import pydantic
import pydantic.generics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = fastapi.FastAPI()
available_templates = {}
authentication = collections.defaultdict(list)

# Tell RQ what Redis connection to use
redis_conn = Redis(host="localhost")
q = Queue("process", connection=redis_conn)  # no args implies the default queue


def build_error_response(msg, code=-1, status="error"):
    return dict(status=status, success=False, result=dict(description=msg, code=code))


def build_success_response(result, status="success"):
    return dict(status=status, success=True, result=result)


def check_auth(func):
    @functools.wraps(func)
    def login_required(*args, **kwargs):
        if "request" in kwargs:
            request = kwargs["request"]
            if len(authentication) == 0:
                request.state.allowed = ["*"]
            else:
                request.state.allowed = []
                if not "Authorization" in request.headers:
                    raise fastapi.HTTPException(status_code=401)
                data = request.headers["Authorization"]
                token = data
                if token in authentication:
                    request.state.allowed = authentication[token]

        return func(*args, **kwargs)

    return login_required


@app.get("/", response_model=schema.Response)
def access_root():
    return build_error_response("Unknown request", 0x0202, "general error")


@app.get("/info", response_model=schema.Response)
@check_auth
def info(request: fastapi.Request):
    know_keys = []
    for key in available_templates:
        if "*" in request.state.allowed or key in request.state.allowed:
            know_keys.append(key)
    return build_success_response(know_keys)


@app.get("/update")
def update_repo():
    repo.update()
    read_templates()
    return build_success_response("update triggered")


@app.get("/status/{jobid}")
@check_auth
def status(request: fastapi.Request, jobid: str = fastapi.Path(...)):
    job = q.fetch_job(jobid)
    if job is None:
        raise fastapi.HTTPException(status_code=404)
    templatename = job.kwargs["template"]["name"]
    if not ("*" in request.state.allowed or templatename in request.state.allowed):
        raise fastapi.HTTPException(status_code=403)
    resp = schema.StatusResult(finished=job.result is not None)
    return build_success_response(resp)

def get_job(jobid, request):
    job = q.fetch_job(jobid)
    if job is None:
        raise fastapi.HTTPException(status_code=404)
    templatename = job.kwargs["template"]["name"]
    if not ("*" in request.state.allowed or templatename in request.state.allowed):
        raise fastapi.HTTPException(status_code=403)
    return job

@app.get("/result/{jobid}")
@check_auth
def result(request: fastapi.Request, jobid: str = fastapi.Path(...)):
    job = get_job(jobid, request)
    print(job.result)
    resp = schema.StatusResult(finished=job.result is not None)
    return build_success_response(resp)

@app.get("/result/{jobid}/log")
@check_auth
def resut_zip(request: fastapi.Request, jobid: str = fastapi.Path(...)):
    job = get_job(jobid, request)
    return PlainTextResponse(job.result['log'])

@app.get("/result/{jobid}/result.zip")
@check_auth
def resut_zip(request: fastapi.Request, jobid: str = fastapi.Path(...)):
    job = get_job(jobid, request)
    return FileResponse(job.result['result_folder'] / 'result.zip', media_type='application/octet-stream',filename='result.zip') 

@app.post("/process/{templatename}")
@check_auth
def process_template(
    request: fastapi.Request,
    templatename: str = fastapi.Path(...),
    data=fastapi.Body(...),
):
    if not ("*" in request.state.allowed or templatename in request.state.allowed):
        raise HTTPException(status_code=403)
    read_templates()
    template = available_templates[templatename]
    logger.info(data)
    job = q.enqueue(processor.process_template, template=template, data=data)
    resp = schema.RequestResult(
        template=templatename,
        request_id=job.id,
        request_timestamp=datetime.datetime.now().timestamp(),
    )
    return build_success_response(resp)



@app.post("/process")
@check_auth
def autoprocess(request: fastapi.Request, data=fastapi.Body(...)):
    logger.info("autotemplate")
    read_templates()
    logger.info("json: {}".format(data))
    use_templates = []
    for name, template in available_templates.items():
        logger.info(f"check process {name}")
        if "selector" in template["config"]:
            for selector in template["config"]["selector"]:
                use = (
                    processor.process_string(f"{{{{ {selector} }}}}", {"data": data})
                    == "True"
                )
                logger.info(f"check: {{{{ {selector} }}}} => {use}")
                if use:
                    if not (
                        "*" in request.state.allowed or name in request.state.allowed
                    ):
                        continue
                    use_templates.append(name)
    jobs = []
    for template in use_templates:
        job = q.enqueue(
            processor.process_template,
            template=available_templates[template],
            data=data,
        )
        resp = schema.RequestResult(
            template=template,
            request_id=job.id,
            request_timestamp=datetime.datetime.now().timestamp(),
        )
        jobs.append(resp)
    return build_success_response(schema.MultipleRequestsResult(requests=jobs))


def read_templates():
    authentication.clear()
    base = pathlib.PosixPath("repo")

    try:
        baseconfig = yaml.load(open(base / "config.yml"), Loader=yaml.CLoader)
    except FileNotFoundError:
        baseconfig = {}

    if "access" in baseconfig:
        for e in baseconfig["access"]:
            if isinstance(e, str):
                authentication[e] = ["*"]
            elif isinstance(e, dict):
                if isinstance(e["templates"], str):
                    authentication[e["token"]] = [e["templates"]]
                else:
                    authentication[e["token"]] = [].expand(e["templates"])
        del baseconfig["access"]

    try:
        dirs = [x for x in next(os.walk(base))[1] if not x.startswith(".")]
    except (FileNotFoundError, StopIteration):
        dirs = []

    for dirname in dirs:
        path = base / dirname
        available_templates[dirname] = {}
        template = available_templates[dirname]
        template["path"] = str(path)
        template["name"] = dirname
        template["config"] = copy.deepcopy(baseconfig)
        with contextlib.suppress(FileNotFoundError):
            template["config"].update(
                yaml.load(open(path / "config.yml"), Loader=yaml.CLoader)
            )
            if "access" in template["config"]:
                for e in template["config"]["access"]:
                    if isinstance(e, str):
                        authentication[e].append(dirname)


update_repo()

def main():
    raise NotImplementedError()
