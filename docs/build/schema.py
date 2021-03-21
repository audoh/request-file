from sys import argv

from request_file.model import RequestFile


def build_schema(path: str) -> None:
    with open(path, "w") as fp:
        fp.write(RequestFile.schema_json(indent=2))
        fp.write("\n")


if __name__ == "__main__":
    build_schema(path=argv[1])
