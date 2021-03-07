SCRIPT_DIR="$(dirname "${BASH_SOURCE}")"
ROOT_DIR="$SCRIPT_DIR/.."
cd "$ROOT_DIR"
PYTHONPATH="$ROOT_DIR/src" poetry run python -m request_file.main "$@"
