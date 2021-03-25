from typing import Dict

from request_file.files import read_var, write_var


class InputHistory:
    _NAMESPACE_KEY = "REQUESTFILE_NAMESPACE"

    def __init__(self) -> None:
        self._inputs: Dict[str, Dict[str, str]] = {}

    def update_input(self, name: str, value: str, namespace: str = "") -> None:
        ns = self._inputs.get(namespace, {})
        ns[name] = value
        self._inputs[namespace] = ns

    def get_last_input(self, name: str, namespace: str = "") -> str:
        ns = self._inputs.get(namespace, {})
        return ns.get(name, "")

    def read_input_file(self, path: str) -> None:
        namespace: str = ""
        with open(path, "r") as fp:
            for line in fp:
                try:
                    key, value = read_var(line)
                except ValueError:
                    continue
                if key == InputHistory._NAMESPACE_KEY:
                    namespace = value
                    continue

                ns = self._inputs.get(namespace, {})
                ns[key] = value
                self._inputs[namespace] = ns

    def write_input_file(self, path: str) -> None:
        with open(path, "w") as fp:
            for namespace, ns in self._inputs.items():
                line = write_var(InputHistory._NAMESPACE_KEY, namespace)
                fp.write(line)
                fp.write("\n")
                for key, value in ns.items():
                    line = write_var(key, value)
                    fp.write(line)
                    fp.write("\n")
            fp.write("\n")
