import argparse
import atexit
from argparse import ArgumentParser
from dataclasses import dataclass
from os import getenv, path
from sys import argv
from typing import Iterable, List, Tuple

import requests

from request_file import model
from request_file.export import export, export_file
from request_file.format import Format, format

try:
    import readline
except Exception:
    readline = None


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
    print_exports: bool
    exports_files: List[str]
    output_files: List[str]


histfile = path.expanduser("~/.pyrequestfile-history")


def init_history() -> None:
    if hasattr(readline, "read_history_file"):
        try:
            readline.read_history_file(histfile)
        except IOError:
            pass
        atexit.register(save_history)


def save_history() -> None:
    readline.set_history_length(1000)
    readline.write_history_file(histfile)


if __name__ == "__main__":
    init_history()

    env_namespace = getenv("REQUESTFILE_NAMESPACE", "")
    if env_namespace:
        env_namespace += "_"

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
    parser.add_argument(
        "--print-exports",
        "-p",
        dest="print_exports",
        default=False,
        action="store_true",
    )
    parser.add_argument("--output", "-o", dest="output_files", action="append")
    parser.add_argument("--exports", "-e", dest="exports_files", action="append")
    args = Arguments(**vars(parser.parse_args(argv[1:])))

    replacements = {key: value for key, value in args.replacements}

    for file in args.files:
        mdl = model.RequestFile.load(file)
        for key, _replacement in mdl.replacements.items():
            input_replacement = replacements.get(_replacement.name)
            if input_replacement is None:
                input_replacement = getenv(f"{env_namespace}{_replacement.name}")
            if input_replacement is None and _replacement.default:
                input_replacement = _replacement.default
            if input_replacement is None and _replacement.required:
                input_replacement = input(f"Enter a value for {_replacement.name}: ")
            if input_replacement is None:
                continue
            mdl = mdl.replace(old=key, new=input_replacement)

        if args.print_curl:

            header_string = " ".join(
                f"-H '{key}: {value}'" for key, value in mdl.headers.items()
            )
            print(f"curl -X {mdl.method} {header_string} -d '{mdl.body}' -L {mdl.url}")

        if not args.dry_run:
            res = requests.request(
                method=mdl.method, url=mdl.url, headers=mdl.headers, data=mdl.body
            )
            for file in args.output_files:
                with open(file, "w") as fp:
                    for _str in format(res=res, mdl=mdl, format=args.format):
                        print(_str, file=fp)
            for _str in format(res=res, mdl=mdl, format=args.format):
                print(_str)

            if args.exports_files:
                for file in args.exports_files:
                    export_file(res=res, mdl=mdl, path=file, namespace=env_namespace)
            if args.print_exports:
                for _str in export(res=res, mdl=mdl, namespace=env_namespace):
                    print(_str)
