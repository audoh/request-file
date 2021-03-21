from typing import Tuple


def read_var(line: str) -> Tuple[str, str]:
    """
    Parses a line that may contain a variable assignment.
    """
    stripped = line.lstrip()
    if stripped.startswith("#"):
        raise ValueError("line is a comment")
    key, val = stripped.split("=", maxsplit=1)
    return key, val


def write_var(key: str, value: str) -> str:
    return f"{key}='{value}'"
