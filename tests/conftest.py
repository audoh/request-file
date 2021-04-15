from typing import Set

_args = {
    "--help",
    "-h",
    "--replace",
    "-r",
    "--format",
    "-f",
    "--print-curl",
    "--dry-run",
    "--print-exports",
    "--output",
    "-o",
    "--imports",
    "-i",
    "--exports",
    "-e",
    "--no-prompt",
    "-n",
    "--ignore-redirects"
}


def args(startswith: str = "") -> Set[str]:
    if not startswith:
        return _args
    return {arg for arg in _args if arg.startswith(startswith)}
