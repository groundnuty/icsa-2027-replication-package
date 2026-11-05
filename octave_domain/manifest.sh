#!/bin/bash
# sha256 and size of every file of the whole-domain run, in parallel; one line per file: "<sha256>  <size>  <path relative to the run dir>"
# usage: manifest.sh <run dir> <out file> [parallelism]
set -eu
run=$1; out=$2; par=${3:-8}
cd "$run"
find . -type f ! -path './tmp/*' ! -path './pylib/*' ! -name 'manifest*.txt' -print0 | sort -z |
  xargs -0 -P "$par" -n 4 bash -c 'for f in "$@"; do printf "%s  %s  %s\n" "$(sha256sum "$f" | cut -d" " -f1)" "$(stat -c %s "$f")" "$f"; done' _ |
  sort -k3 > "$out"
wc -l "$out"
