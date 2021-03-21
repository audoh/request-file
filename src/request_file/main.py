import argparse
import atexit
from argparse import ArgumentParser
from dataclasses import dataclass
from os import getenv, makedirs, path
from sys import argv
from typing import Iterable, List, Tuple

import requests
from appdirs import user_state_dir

from request_file import model
from request_file.export import export, export_file
from request_file.files import read_var
from request_file.format import Format, format
from request_file.history import InputHistory

try:
    import readline
except Exception:
    readline = None


def _parse_replacement(input: str) -> Tuple[str, str]:
    try:
        key, value = read_var(input)
    except ValueError as exc:
        raise ValueError(f"key is required") from exc
    return key, value


@dataclass
class _Arguments(argparse.Namespace):
    files: Iterable[str]
    replacements: Iterable[Tuple[str, str]]
    format: Format
    dry_run: bool
    print_curl: bool
    print_exports: bool
    exports_files: List[str]
    output_files: List[str]


_state_dir = user_state_dir("request-file", "audoh")
_input_history_path = path.join(_state_dir, "last-inputs")
_readline_history_path = path.join(_state_dir, "readline-history")
_input_history = InputHistory()


def _init_history() -> None:
    try:
        _input_history.read_input_file(_input_history_path)
    except IOError:
        pass
    if hasattr(readline, "read_history_file"):
        try:
            readline.read_history_file(_readline_history_path)
        except IOError:
            pass


def _save_history() -> None:
    makedirs(_state_dir, exist_ok=True)
    _input_history.write_input_file(_input_history_path)
    if hasattr(readline, "read_history_file"):
        readline.set_history_length(1000)
        readline.write_history_file(_readline_history_path)


if __name__ == "__main__":
    _init_history()
    atexit.register(_save_history)

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
        type=_parse_replacement,
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
    parser.add_argument(
        "--output", "-o", dest="output_files", action="append", default=[]
    )
    parser.add_argument(
        "--exports", "-e", dest="exports_files", action="append", default=[]
    )
    args = _Arguments(**vars(parser.parse_args(argv[1:])))

    replacements = {key: value for key, value in args.replacements}

    for file in args.files:
        mdl = model.RequestFile.load(file)
        for key, replacement in mdl.replacements.items():
            # Use explicit argument first
            input_replacement = replacements.get(replacement.name)
            # Try to use environment var second
            if input_replacement is None:
                input_replacement = getenv(f"{env_namespace}{replacement.name}")
            # Use default value third if specified but offer the ability to override it
            default_value = replacement.default or _input_history.get_last_input(
                replacement.name, namespace=env_namespace
            )
            if input_replacement is None and default_value:
                input_replacement = input(
                    f"Enter a value for {replacement.name} ({default_value}): "
                )
                if input_replacement:
                    _input_history.update_input(
                        replacement.name, input_replacement, namespace=env_namespace
                    )
                else:
                    input_replacement = default_value
            # If no default specified but the replacement is required, prompt for value
            if input_replacement is None and replacement.required:
                input_replacement = input(f"Enter a value for {replacement.name}: ")
                if input_replacement:
                    _input_history.update_input(
                        replacement.name, input_replacement, namespace=env_namespace
                    )
            # If we still haven't got a replacement then leave as-is
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
