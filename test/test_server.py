import pytest
import tempfile
import io
from httypist import server


@pytest.fixture
def client():
    server.app.config["TESTING"] = True

    with server.app.test_client() as client:
        yield client


@pytest.fixture
def gitrepo():
    tempdir = tempfile.TemporaryDirectory()


def test__test():
    assert True


def test__index_no_get(client):
    r = client.get("/")
    assert r.status_code == 405


def test__index_post_no_data(client):
    r = client.post("/")
    assert r.status_code == 400
    assert b"unable to determine" in r.data


def test__index_post_with_invalid_mainfile(client):
    r = client.post("/", data={"main": "test"})
    assert r.status_code == 400


def test__index_post_with_valid_mainfile(client):
    r = client.post(
        "/",
        data={
            "main": "test.tex",
            "test.tex": (
                io.BytesIO(
                    b"\\documentclass{scrartcl}\n\\begin{document}Hello World\\end{document}"
                ),
                "test.tex",
            ),
        },
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    assert b"%PDF" in r.data
    assert len(r.data) > 2000
