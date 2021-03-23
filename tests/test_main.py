import pytest
from py.path import local
from request_file.main import main
from request_file.model import RequestFile
from requests_mock import Mocker


def call(*args: str) -> None:
    main("main", *args)


def test_plain_get(tmpdir: local, requests_mock: Mocker) -> None:
    mocker = requests_mock.get("https://example.com", text="")
    file = tmpdir / "file.json"
    with open(file, "w") as fp:
        file.write(RequestFile(url="https://example.com").json())
    call(file.strpath)
    assert mocker.called_once
