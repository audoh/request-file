#!/bin/bash

_requestfile() {
  local comp_cword="$1"
  shift 1
  local comp_words=("$@")

  compopt -o nospace

  [ -n "$comp_cword" ] && [ "$comp_cword" -ge 0 ] 2>/dev/null
  if [ $? -ne 0 ]; then
    echo error: arg 1 must be integer index of current word >&2
    return
  fi

  local cur="${comp_words[comp_cword]}"

  # Check we don't have --
  local allow_opt=true
  local idx=0
  until [ "$idx" -eq "$comp_cword" ]; do
    local word="${comp_words[$idx]}"
    if [ "$word" == "--" ]; then
      allow_opt=falsebreak
    fi
    idx=$(($idx + 1))
  done
  unset idx

  if [ "$allow_opt" = true ]; then
    if [ "$comp_cword" -ge 1 ]; then
      local prev="${comp_words[comp_cword-1]}"

      if [ "$prev" == "--replace" ] || [ "$prev" == "-r" ]; then
        return
      elif [ "$prev" == "--format" ] || [ "$prev" == "-f" ]; then
        local formats
        formats="$formats body"
        formats="$formats verbose"
        formats="$formats requests-mock"
        compgen -W "$formats" -- "$cur"
        return
      elif [ "$prev" == "--output" ] || [ "$prev" == "-o" ] || \
          [ "$prev" == "--exports" ] || [ "$prev" == "-e" ]; then
        compgen -f -- "$cur"
        return
      fi
    fi

    local opts="--replace -r"
    opts="$opts --format -f"
    opts="$opts --print-curl -c"
    opts="$opts --dry-run -d"
    opts="$opts --print-exports -p"
    opts="$opts --output -o"
    opts="$opts --exports -e"
    compgen -W "$opts" -- "$cur"

  fi

  files=`compgen -f -- "$cur" | grep .json$`
  dirs=`compgen -d -S / -- "$cur"`

  for file in "$files"; do
    echo "$file"
  done

  for dir in "$dirs"; do
    echo "$dir"
  done

}

_requestfile "$@"
