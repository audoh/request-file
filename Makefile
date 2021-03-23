_path := $(abspath $(lastword $(MAKEFILE_LIST)))
_dir := $(dir $(_path))
export PYTHONPATH := $(_dir)src

.PHONY: build
build:
	poetry run python -m nuitka --follow-imports src/request_file/main.py --output-dir=build

.PHONY: schema
schema:
	poetry run python docs/build/schema.py docs/schema.json

.PHONY: tests
tests:
	poetry run pytest --testdox
