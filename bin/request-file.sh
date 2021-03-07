ROOT_DIR="$(dirname "${BASH_SOURCE}")"
PYTHONPATH="$ROOT_DIR/../src" poetry run python -m request_file.main "$@"
