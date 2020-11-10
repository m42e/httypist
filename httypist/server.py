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

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = fastapi.FastAPI()
available_templates = {}
authentication = collections.defaultdict(list)

# Tell RQ what Redis connection to use
redis_conn = Redis(host="localhost")
q = Queue("process", connection=redis_conn)  # no args implies the default queue


def build_error_response(msg, code=-1, status="error"):
    """Make Error Response based on the message and code"""
    return dict(status=status, success=False, result=dict(description=msg, code=code))


def build_success_response(result, status="success"):
    """Make Success Response based on the result"""
    return dict(status=status, success=True, result=result)


def check_auth(func):
    """Decorate the routes to get a basic protection information. The allowed templates are stored in the request.state as allowed.
    N.B.:
        - The real check if the template is allowed with the provided `Authorization` header is not done here as we may not know, what template to use.
        - It is required that the decorated function includes a request:fastapi.Request parameter.
    """

    @functools.wraps(func)
    async def login_required(*args, **kwargs):
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

        return await func(*args, **kwargs)

    return login_required


@app.get("/", response_model=schema.Response)
def access_root():
    '''Always return an error on index'''
    return build_error_response("Unknown request", 0x0202, "general error")


@app.get("/info", response_model=schema.Response)
@check_auth
async def info(request: fastapi.Request):
    '''Return the available templates (respecting the given authentication)'''
    know_keys = []
    for key in available_templates:
        if "*" in request.state.allowed or key in request.state.allowed:
            know_keys.append(key)
    return build_success_response(know_keys)


@app.get("/update")
def update_repo():
    '''Refresh the repository'''
    repo.update()
    read_templates()
    return build_success_response("update triggered")


def get_job(jobid, request):
    job = q.fetch_job(jobid)
    if job is None:
        raise fastapi.HTTPException(status_code=404)
    templatename = job.kwargs["template"]["name"]
    if not ("*" in request.state.allowed or templatename in request.state.allowed):
        raise fastapi.HTTPException(status_code=403)
    return job

@app.get("/status/{jobid}")
@check_auth
async def status(request: fastapi.Request, jobid: str = fastapi.Path(...)):
    '''Check the state of a triggered httypist job.'''
    job = get_job(jobid, request)
    resp = schema.StatusResult(finished=job.result is not None)
    return build_success_response(resp)



@app.get("/result/{jobid}")
@check_auth
async def result(request: fastapi.Request, jobid: str = fastapi.Path(...)):
    '''Get the result information for a specific job.'''
    job = get_job(jobid, request)
    resp = schema.StatusResult(finished=job.result is not None)
    return build_success_response(resp)


@app.get("/result/{jobid}/log")
@check_auth
async def resut_zip(request: fastapi.Request, jobid: str = fastapi.Path(...)):
    '''Get the log of a job.'''
    job = get_job(jobid, request)
    return PlainTextResponse(job.result["log"])


@app.get("/result/{jobid}/result.zip")
@check_auth
async def resut_zip(request: fastapi.Request, jobid: str = fastapi.Path(...)):
    '''Get the result files of a job.'''
    job = get_job(jobid, request)
    return FileResponse(
        job.result["result_folder"] / "result.zip",
        media_type="application/octet-stream",
        filename=f"result-{jobid}.zip",
    )

@app.get("/result/{jobid}/temp.zip")
@check_auth
async def temp_zip(request: fastapi.Request, jobid: str = fastapi.Path(...)):
    '''Get the temporary files of a job.'''
    job = get_job(jobid, request)
    return FileResponse(
        job.result["result_folder"] / "temp.zip",
        media_type="application/octet-stream",
        filename=f"temp-{jobid}.zip",
    )


async def get_all_available_data(request):
    try:
        json = await request.json()
    except:
        json = None
    body = await request.body()
    return dict(
        body=body,
        json=json,
        headers=dict(request.headers),
        query=dict(request.query_params),
        client=request.client.host,
    )

@app.post("/process/{templatename}")
@check_auth
async def process_template(
    request: fastapi.Request,
    templatename: str = fastapi.Path(...),
):
    '''This triggers the processing of a given template with the data provided in the request'''
    if not ("*" in request.state.allowed or templatename in request.state.allowed):
        raise fastapi.HTTPException(status_code=403)
    if templatename not in available_templates:
        raise fastapi.HTTPException(status_code=404)
    template = available_templates[templatename]
    alldata = await get_all_available_data(request)
    job = q.enqueue(processor.process_template, template=template, data=alldata)
    resp = schema.RequestResult(
        template=templatename,
        request_id=job.id,
        request_timestamp=datetime.datetime.now().timestamp(),
    )
    return build_success_response(resp)



@app.post("/process")
@check_auth
async def autoprocess(request: fastapi.Request):
    '''This triggers the processing of a template with the data provided in the request. The template will be selected based on the data provided and the selector in the template config.'''
    logger.info("autotemplate")
    alldata = await get_all_available_data(request)
    logger.debug("data: {}".format(alldata))
    use_templates = []
    for name, template in available_templates.items():
        logger.debug(f"check process {name}")
        if "selector" in template["config"]:
            for selector in template["config"]["selector"]:
                use = (
                    processor.process_string(f"{{{{ {selector} }}}}", alldata)
                    == "True"
                )
                logger.debug(f"check: {{{{ {selector} }}}} => {use}")
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
        baseconfig = yaml.load(open(base / "config.yml"), Loader=Loader)
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
                yaml.load(open(path / "config.yml"), Loader=Loader)
            )
            if "access" in template["config"]:
                for e in template["config"]["access"]:
                    if isinstance(e, str):
                        authentication[e].append(dirname)


update_repo()


def main():
    raise NotImplementedError()
