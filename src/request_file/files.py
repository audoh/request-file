import re
from typing import Iterable, Tuple

_re = None


def _get_re():
    global _re
    if _re is not None:
        return _re
    _re = re.compile(
        r"""(?:^|;)\s*([a-z_][a-z_0-9]*)=(?:'([^']*)'|"([^"]*)"|([^\s]*))\s*(?:$|;)""",
        flags=re.IGNORECASE,
    )
    return _re


def read_vars(line: str) -> Iterable[Tuple[str, str]]:
    for match in _get_re().finditer(line):
        key = match.group(1)
        value = match.group(2) or match.group(3) or match.group(4)
        yield key, value


def read_var(line: str) -> Tuple[str, str]:
    """
    Parses a line that may contain a variable assignment.
    """
    try:
        return next(iter(read_vars(line)))
    except StopIteration as exc:
        raise ValueError("error") from exc


def write_var(key: str, value: str) -> str:
    return f"{key}='{value}'"
