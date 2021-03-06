import typing as t
import datetime

from pydantic import BaseModel

from enum import Enum


class Response(BaseModel):
    status: str
    success: bool
    result: t.Union["ErrorResult", "RequestResult", "StatusResult", "RespsoneResult", "MultipleRequestsResult", str]

    class Config:
        schema_extra = {
            "example": {"status": "ok", "success": True, "result": "object"}
        }


class ErrorResult(BaseModel):
    description: str
    code: int



class RequestResult(BaseModel):
    template: str
    request_id: str
    request_timestamp: int

class MultipleRequestsResult(BaseModel):
    requests: t.List[RequestResult]

class StatusResult(BaseModel):
    finished: bool


class RespsoneResult(BaseModel):
    original_request: RequestResult
    log: t.List[str]
    result_files: t.List[str]
    result_zip: str
    folder_zip: str

class TemplatesResult(BaseModel):
    templates: t.List[str]
