#!/bin/bash

_requestfile() {
  local comp_cword="$1"
  shift 1
  local comp_words=("$@")

  [ -n "$comp_cword" ] && [ "$comp_cword" -ge 0 ] 2>/dev/null
  if [ $? -ne 0 ]; then
    echo error: arg 1 must be integer index of current word >&2
    return
  fi

  local cur="${comp_words[comp_cword]}"

  if [ "$comp_cword" -ge 1 ]; then
    local prev="${comp_cwords[comp_cword-1]}"
  fi

  # Default positional argument is a path to a JSON request file
  compgen -f "$cur" | grep .json$
}

_requestfile "$@"
