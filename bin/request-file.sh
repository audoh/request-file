log() {
  if [ -z "$REQUESTFILEDEBUG" ]; then
    return 0
  fi
  echo $@ >&2
}

SCRIPT_DIR="$(dirname "${BASH_SOURCE}")"
ROOT_DIR="$SCRIPT_DIR/.."

# Activate venv
log Activating venv
pushd "$ROOT_DIR" > /dev/null
VENV_DIR=`poetry env info -p`
popd > /dev/null
source $VENV_DIR/bin/activate

# Run script
log Running script
export PYTHONPATH="$ROOT_DIR/src"
python -m request_file.main "$@"
