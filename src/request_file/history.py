from typing import Dict

from request_file.files import read_var, write_var


class InputHistory:
    _inputs: Dict[str, str]

    def __init__(self) -> None:
        self._inputs: Dict[str, str] = {}

    def update_input(self, name: str, value: str) -> None:
        self._inputs[name] = value

    def get_last_input(self, name: str) -> str:
        return self._inputs.get(name, "")

    def read_input_file(self, path: str) -> None:
        with open(path, "r") as fp:
            for line in fp:
                try:
                    key, value = read_var(line)
                except ValueError:
                    continue
                self._inputs[key] = value

    def write_input_file(self, path: str) -> None:
        with open(path, "w") as fp:
            for key, value in self._inputs.items():
                line = write_var(key, value)
                fp.write(line)
                fp.write("\n")
