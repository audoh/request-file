import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple, Union

from requests import Response

from request_file.model import RequestFile


class PathspecType(str, Enum):
    JSON = "json"


class JSONPathError(ValueError):
    def __init__(
        self, *, message: str = "bad path", pos: List[str], value: Any
    ) -> None:
        super().__init__(
            f"bad path '.{'.'.join(pos)}' ( .{'.'.join(pos[:-1])} => {value!r} )"
        )


def read_pathspec(text: str, pathspec: str) -> Any:
    try:
        typesep_idx = pathspec.index(":")
    except (ValueError, IndexError) as exc:
        raise ValueError(f"pathspec must start with 'type:' identifier") from exc

    pathspec_type = pathspec[:typesep_idx]
    path = pathspec[typesep_idx + 1 :]

    if pathspec_type == PathspecType.JSON:
        # e.g. "json:.rootkey.2.otherkey.value"
        # e.g. "json:.3.otherkey.value"

        if not path.startswith("."):
            raise ValueError("json pathspec must start with .")

        _json = json.loads(text)
        parts = path.split(".")[1:]
        pos: List[str] = []
        for part in parts:
            pos.append(part)

            if isinstance(_json, list):
                # Read an index into the list
                try:
                    idx = int(part)
                except ValueError as exc:
                    raise JSONPathError(pos=pos, value=_json) from exc

                try:
                    _json = _json[idx]
                except IndexError as exc:
                    raise JSONPathError(pos=[*pos[:-1], str(idx)], value=_json) from exc

            elif isinstance(_json, dict):
                # Read a key of the dict
                try:
                    _json = _json[part]
                except KeyError as exc:
                    raise JSONPathError(pos=pos, value=_json) from exc

            else:
                # We can't have something other than a dict or a list until the last part
                raise JSONPathError(pos=pos, value=_json)

        return _json
    else:
        valid_values = ", ".join(f"'{v.value}'" for v in PathspecType)
        raise ValueError(
            f"unsupported pathspec type '{pathspec_type}'; valid values are {valid_values}"
        )


def export(res: Response, mdl: RequestFile) -> Iterable[Union[str, bytes]]:
    for key, pathspec in mdl.exports.items():
        try:
            value = read_pathspec(text=res.text, pathspec=pathspec)
        except Exception:
            value = ""
        yield f"{key}='{value}'"


def export_file(res: Response, mdl: RequestFile, path: str) -> None:
    existing: Dict[str, int] = {}
    lines: List[str] = []
    try:
        with open(path, "r") as fp:
            for line in fp:
                line_no = len(lines)
                lines.append(line)
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                try:
                    key = line[: line.index("=")]
                except ValueError:
                    continue
                existing[key] = line_no
    except FileNotFoundError:
        pass

    for key, pathspec in mdl.exports.items():
        try:
            value = read_pathspec(text=res.text, pathspec=pathspec)
        except Exception:
            value = ""
        line = f"{key}='{value}'\n"
        if key in existing:
            line_no = existing[key]
            lines[line_no] = line
        else:
            lines.append(line)

    with open(path, "w") as fp:
        fp.writelines(lines)
        fp.write("\n")


if __name__ == "__main__":
    print(read_pathspec(json.dumps({"a": [{"b": "c"}]}), pathspec="jsons:.a.0.b"))
