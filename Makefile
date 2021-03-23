_path := $(abspath $(lastword $(MAKEFILE_LIST)))
_dir := $(dir $(_path))
export PYTHONPATH := $(_dir)src


build: .venv $(wildcard src/**/*.py)
	poetry run python -m nuitka --follow-imports src/request_file/main.py --output-dir=build
	cp build/main.bin bin/request-file.bin 2> /dev/null || true
	cp build/main.exe bin/request-file.exe 2> /dev/null || true


.PHONY: schema
schema: docs/schema.json

.PHONY: tests
tests: .venv
	poetry run pytest --testdox

all: build schema tests

docs/schema.json: .venv docs/build/schema.py $(wildcard src/**/*.py)
	poetry run python docs/build/schema.py docs/schema.json

.venv: poetry.lock
	poetry install
