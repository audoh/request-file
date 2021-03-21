#!/bin/bash

_requestfile() {
  local comp_cword="$1"
  shift 1
  local comp_words=("$@")

  # Check args are in the format 0 WORD0 WORD1 WORD2
  [ -n "$comp_cword" ] && [ "$comp_cword" -ge 0 ] 2>/dev/null
  if [ $? -ne 0 ]; then
    echo error: arg 1 must be integer index of current word >&2
    return
  fi


  # Check we don't have -- (end of options marker)
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

  local curword="${comp_words[comp_cword]}"
  if [ "$allow_opt" = true ]; then
    if [ "$comp_cword" -ge 1 ]; then
      local prevword="${comp_words[comp_cword-1]}"

      if [ "$prevword" == "--replace" ] || [ "$prevword" == "-r" ]; then
        return
      elif [ "$prevword" == "--format" ] || [ "$prevword" == "-f" ]; then
        local formats
        formats="$formats body"
        formats="$formats verbose"
        formats="$formats requests-mock"
        compgen -W "$formats" -- "$curword"
        return
      elif [ "$prevword" == "--output" ] || [ "$prevword" == "-o" ] || \
          [ "$prevword" == "--exports" ] || [ "$prevword" == "-e" ]; then
        compgen -f -- "$curword"
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
    compgen -W "$opts" -- "$curword"
  fi

  files=`compgen -f -- "$curword" | grep .json$`
  dirs=`compgen -d -S / -- "$curword"`


  if [ -n "$dirs" ] && [ `echo "$dirs" | wc -l` -eq 1 ] && [ -z "$files" ]; then
    # Having no luck whatsoever with compopt to disable the trailing space and the documentation is minimal
    # Making bash think it needs to stop to let you decide between the dir and some random gibberish works as well as anything
    # The reason this works is because although it's adding another result, once there is a trailing slash, compgen will look in that directory for results
    # Tab-completion will therefore then move to the next folder, and the process will repeat until we either start finding files or $dirs becomes empty
    echo "${dirs[0]}asdf"
  fi

  for file in "$files"; do
    if [ -n "$file" ]; then
      echo "$file"
    fi
  done

  for dir in "$dirs"; do
    if [ -n "$dir" ]; then
      echo "$dir"
    fi
  done
}

_requestfile "$@"
unset _requestfile
