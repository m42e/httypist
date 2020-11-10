import pytest
import shutil
import os
import tempfile
import io
from httypist import server
from fastapi.testclient import TestClient

from httpx import AsyncClient



@pytest.fixture
def client():
    return TestClient(server.app)


@pytest.fixture
def gitrepo():
    tempdir = tempfile.TemporaryDirectory()
    os.environ["GIT_URL"] = tempdir.name
    return tempdir


def test__test():
    assert True


def test__index_no_get(client):
    r = client.get("/")
    assert r.status_code == 200


def test__index_post_no_data(client):
    r = client.post("/")
    assert r.status_code == 405


def test__index_post_with_invalid_mainfile(client):
    r = client.post("/", data={"main": "test"})
    assert r.status_code == 405


# def test_info(client):
#     r = client.get("/info")
#     assert r.status_code == 401
# 
# @pytest.mark.asyncio
# async def test_info_authenticated(gitrepo):
#     async with AsyncClient(app=server.app, base_url="http://test") as ac:
#         r = await ac.get("/update")
#         response = await ac.get("/info", headers={'Authorization': 'testkey'})
#     assert r.status_code == 200
# 
# @pytest.mark.asyncio
# async def test_test(gitrepo):
#     async with AsyncClient(app=server.app, base_url="http://test") as ac:
#         r = await ac.get("/update")
#         r = await ac.post("/process/test", headers={'Authorization': 'testkey'}, data={'name':'matthias'})
#     assert r.status_code == 200
#     print(r.content)



