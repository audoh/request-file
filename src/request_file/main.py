import argparse
import atexit
import json
from argparse import ArgumentParser
from base64 import b64encode
from dataclasses import dataclass
from enum import Enum
from os import getenv, path
from sys import argv, stderr
from typing import Iterable, Tuple

import requests

from . import model

try:
    import readline
except Exception:
    readline = None


class Format(str, Enum):
    BODY = "body"
    VERBOSE = "verbose"
    REQUESTS_MOCK = "requests-mock"
    DEFAULT = BODY


def replacement(input: str) -> Tuple[str, str]:
    key, value = input.split("=")
    if not key:
        raise ValueError(f"key is required")
    return key, value


@dataclass
class Arguments(argparse.Namespace):
    files: Iterable[str]
    replacements: Iterable[Tuple[str, str]]
    format: Format
    dry_run: bool
    print_curl: bool


histfile = path.expanduser("~/.pyrequestfile-history")


def init_history() -> None:
    if hasattr(readline, "read_history_file"):
        try:
            readline.read_history_file(histfile)
        except IOError:
            pass
        atexit.register(save_history, histfile)


def save_history() -> None:
    readline.set_history_length(1000)
    readline.write_history_file(histfile)


if __name__ == "__main__":
    init_history()

    parser = ArgumentParser()
    parser.add_argument("files", type=str, nargs="+")
    parser.add_argument(
        "--replace",
        "-r",
        dest="replacements",
        default=[],
        type=replacement,
        action="append",
    )
    parser.add_argument(
        "--format", "-f", dest="format", default=Format.DEFAULT, type=Format
    )
    parser.add_argument(
        "--print-curl", "-c", dest="print_curl", default=False, action="store_true"
    )
    parser.add_argument(
        "--dry-run", "-d", dest="dry_run", default=False, action="store_true"
    )
    args = Arguments(**vars(parser.parse_args(argv[1:])))

    replacements = {key: value for key, value in args.replacements}

    for file in args.files:
        mdl = model.RequestFile.load(file)
        for key, _replacement in mdl.replacements.items():
            input_replacement = replacements.get(_replacement.name)
            if input_replacement is None:
                input_replacement = getenv(_replacement.name)
            if input_replacement is None and _replacement.default:
                input_replacement = _replacement.default
            if input_replacement is None and _replacement.required:
                print(f"Enter a value for {_replacement.name}: ", file=stderr, end="")
                input_replacement = input()
            if input_replacement is None:
                continue
            mdl = mdl.replace(old=key, new=input_replacement)

        if args.print_curl:
            header_string = " ".join(
                f"-H '{key}: {value}" for key, value in mdl.headers.items()
            )
            print(
                f"curl -L -X {mdl.method} {header_string} -d '{mdl.body}' {mdl.url}",
                file=stderr,
            )

        if not args.dry_run:
            res = requests.request(
                method=mdl.method, url=mdl.url, headers=mdl.headers, data=mdl.body
            )

            if args.format == Format.BODY:
                try:
                    _json = res.json()
                    print(json.dumps(_json, indent=2))
                except ValueError:
                    print(res.text)

            elif args.format == Format.REQUESTS_MOCK:
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
                    content_type = res.headers.get("content-type", "text/plain").split(
                        ";"
                    )[0]
                    if content_type.startswith("text/"):
                        mock_args["text"] = res.text
                    else:
                        mock_args["content"] = str(
                            b64encode(res.content), encoding="utf-8"
                        )
                else:
                    mock_args["json"] = res_json
                print(json.dumps(mock_args, indent=2))

            elif args.format == Format.VERBOSE:
                print(f"Status: {res.status_code} {res.reason}")
                for key, value in res.headers.items():
                    print(f"{key}: {value}")
                print("Body:")
                try:
                    _json = res.json()
                    print(json.dumps(_json, indent=2))
                except ValueError:
                    print(res.text)
