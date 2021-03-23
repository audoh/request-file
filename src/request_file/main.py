import argparse
import atexit
from argparse import ArgumentParser
from dataclasses import dataclass
from os import environ, makedirs, path
from sys import argv, stderr
from typing import Dict, Iterable, List, Tuple
from urllib import parse as urlparse

import requests
from appdirs import user_state_dir

from request_file import model
from request_file.export import get_exports, save_exports
from request_file.files import read_var, write_var
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
    no_prompt: bool


_state_dir = user_state_dir("request-file", "audoh")
_input_history_path = path.join(_state_dir, "last-inputs")
_readline_history_path = path.join(_state_dir, "readline-history")
_env_path = path.join(_state_dir, "environment")
_input_history = InputHistory()
_exported_vars: Dict[str, str] = {}


def _init_history() -> None:
    # Read input history
    try:
        _input_history.read_input_file(_input_history_path)
    except IOError:
        pass
    # Read readline history
    if hasattr(readline, "read_history_file"):
        try:
            readline.read_history_file(_readline_history_path)
        except IOError:
            pass
    # Read exports
    try:
        with open(_env_path, "r") as fp:
            for line in fp:
                try:
                    k, v = read_var(line)
                except ValueError:
                    continue
                environ[k] = v
                _exported_vars[k] = v
    except IOError:
        pass


def _save_history() -> None:
    makedirs(_state_dir, exist_ok=True)
    # Save input history
    _input_history.write_input_file(_input_history_path)
    # Save readline history
    if hasattr(readline, "read_history_file"):
        readline.set_history_length(1000)
        readline.write_history_file(_readline_history_path)
    # Save exports
    with open(_env_path, "w") as fp:
        for k, v in _exported_vars.items():
            fp.write(write_var(k, v))
            fp.write("\n")
        fp.write("\n")


if __name__ == "__main__":
    _init_history()
    atexit.register(_save_history)

    namespace = environ.get("REQUESTFILE_NAMESPACE", "")
    env_prefix = namespace
    if env_prefix:
        env_prefix += "_"

    # Arg parsing
    parser = ArgumentParser()
    parser.add_argument(
        "files",
        type=str,
        nargs="+",
        help="JSON files which follow the Request File schema.",
    )
    parser.add_argument(
        "--replace",
        "-r",
        dest="replacements",
        metavar="REPLACEMENT=VALUE",
        default=[],
        type=_parse_replacement,
        action="append",
    )
    parser.add_argument(
        "--format",
        "-f",
        dest="format",
        default=Format.DEFAULT,
        type=Format,
        help="Output format to use.",
    )
    parser.add_argument(
        "--print-curl",
        dest="print_curl",
        default=False,
        action="store_true",
        help="Output the equivalent cURL command to stdout.",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        default=False,
        action="store_true",
        help="Don't send the request. Generally used in combination with --print-curl.",
    )
    parser.add_argument(
        "--print-exports",
        dest="print_exports",
        default=False,
        action="store_true",
        help="Output environment variables read from the response to stdout.",
    )
    parser.add_argument(
        "--output",
        "-o",
        dest="output_files",
        action="append",
        default=[],
        help="Path to a file where the response should be saved. Multiple can be specified.",
    )
    parser.add_argument(
        "--exports",
        "-e",
        dest="exports_files",
        action="append",
        default=[],
        help="Path to a file where environment variables read from the response should be saved. Multiple can be specified.",
    )
    parser.add_argument(
        "--no-prompt",
        "-n",
        dest="no_prompt",
        default=False,
        action="store_true",
        help="When values are not set in the environment, don't prompt for them. Use the defaults if available, or otherwise skip them entirely.",
    )
    args = _Arguments(**vars(parser.parse_args(argv[1:])))
    replacements = {key: value for key, value in args.replacements}

    for export_file in args.files:
        mdl = model.RequestFile.load(export_file)

        # Replacement/substitution
        for replacement_key, replacement in mdl.replacements.items():
            # Use explicit argument first
            input_replacement = replacements.get(replacement.name)
            is_set = input_replacement is not None
            # Try to use environment var second
            if not is_set:
                input_replacement = environ.get(f"{env_prefix}{replacement.name}")
                is_set = input_replacement is not None
            # Use default value third if specified but offer the ability to override it
            default_value = (
                replacement.default
                if replacement.has_default
                else _input_history.get_last_input(
                    replacement.name, namespace=namespace
                )
            )
            if not is_set and (replacement.has_default or default_value):
                if not args.no_prompt:
                    input_replacement = input(
                        f"Enter a value for {replacement.name} ({default_value}): "
                    )
                if not args.no_prompt and input_replacement:
                    _input_history.update_input(
                        replacement.name, input_replacement, namespace=namespace
                    )
                else:
                    input_replacement = default_value
                is_set = True
            # If no default specified but the replacement is required, prompt for value
            if not is_set and replacement.required:
                if not args.no_prompt:
                    input_replacement = input(f"Enter a value for {replacement.name}: ")
                    if input_replacement:
                        _input_history.update_input(
                            replacement.name, input_replacement, namespace=namespace
                        )
                        is_set = True
            # If we still haven't got a replacement then leave as-is
            if not is_set:
                continue
            try:
                parsed = (
                    model.parse_replacement(value=input_replacement, model=replacement)
                    if isinstance(input_replacement, str)
                    else input_replacement
                )
            except ValueError as exc:
                print(f"error: {exc}", file=stderr)
                exit(1)
            mdl = model.replace(mdl, old=replacement_key, new=parsed)

        qsl = urlparse.parse_qsl(urlparse.urlparse(mdl.url).query)
        for param, param_value in mdl.params.items():
            if param_value is None:
                continue
            elif isinstance(param_value, str):
                qsl.append((param, param_value))
            else:
                for param_subvalue in param_value:
                    if param_subvalue is None:
                        continue
                    qsl.append((param, param_subvalue))
        qs = urlparse.urlencode(qsl)
        url = urlparse.urljoin(mdl.url, f"?{qs}")

        # cURL
        if args.print_curl:
            header_string = " ".join(
                f"-H '{key}: {value}'" for key, value in mdl.headers.items()
            )

            print(f"curl -X {mdl.method} {header_string} -d '{mdl.body}' -L {url}")

        if not args.dry_run:
            res = requests.request(
                method=mdl.method, url=url, headers=mdl.headers, data=mdl.body
            )

            # Output response
            for export_file in args.output_files:
                with open(export_file, "w") as fp:
                    for format_str in format(res=res, mdl=mdl, format=args.format):
                        print(format_str, file=fp)
            for format_str in format(res=res, mdl=mdl, format=args.format):
                print(format_str)

            # Output environment exports
            for export_key, export_value in get_exports(
                res=res, mdl=mdl, prefix=env_prefix
            ):
                environ[export_key] = export_value
                _exported_vars[export_key] = export_value

            save_exports(res=res, mdl=mdl, path=_env_path, prefix=env_prefix)
            if args.exports_files:
                for export_file in args.exports_files:
                    save_exports(res=res, mdl=mdl, path=export_file, prefix=env_prefix)
            if args.print_exports:
                for export_key, export_value in get_exports(
                    res=res, mdl=mdl, prefix=env_prefix
                ):
                    print(write_var(export_key, export_value))
