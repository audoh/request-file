_path := $(abspath $(lastword $(MAKEFILE_LIST)))
_dir := $(dir $(_path))
export PYTHONPATH := $(_dir)src

build: $(wildcard src/**/*.py) poetry.lock
	poetry run python -m nuitka --follow-imports src/request_file/main.py --output-dir=build
	cp build/main.bin bin/request-file.bin 2> /dev/null || true
	cp build/main.exe bin/request-file.exe 2> /dev/null || true

.PHONY: schema
schema:
	poetry run python docs/build/schema.py docs/schema.json

.PHONY: tests
tests:
	poetry run pytest --testdox

all: build schema tests
