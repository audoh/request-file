import json
from base64 import b64encode
from enum import Enum
from typing import Iterable, Union

from requests import Response

from request_file.model import RequestFile


class Format(str, Enum):
    BODY = "body"
    VERBOSE = "verbose"
    REQUESTS_MOCK = "requests-mock"
    DEFAULT = BODY


def format(
    res: Response, mdl: RequestFile, format: Format
) -> Iterable[Union[str, bytes]]:
    if format == Format.BODY:
        try:
            _json = res.json()
            yield json.dumps(_json, indent=2)
        except ValueError:
            yield res.text
        return

    elif format == Format.REQUESTS_MOCK:
        mock_args = {
            "method": mdl.method,
            "url": res.url,
            "status_code": res.status_code,
            "reason": res.reason,
            "request_headers": mdl.headers,
            "headers": dict(res.headers),
        }
        try:
            res_json = res.json()
        except ValueError:
            content_type = res.headers.get("content-type", "text/plain").split(";")[0]
            if content_type.startswith("text/"):
                mock_args["text"] = res.text
            else:
                mock_args["content"] = str(b64encode(res.content), encoding="utf-8")
        else:
            mock_args["json"] = res_json
        yield json.dumps(mock_args, indent=2)
        return

    elif format == Format.VERBOSE:
        yield f"Status: {res.status_code} {res.reason}"
        for key, value in res.headers.items():
            yield f"{key}: {value}"
        yield "Body:"
        try:
            _json = res.json()
            yield json.dumps(_json, indent=2)
        except ValueError:
            yield res.text
        return
