#!/usr/bin/env bash
# The M+ driver (science #34, 4 Nov 18:53Z). Run ON .23. DRY by default (validates and prints; starts nothing, reads neither site_g nor site_f); `--run` acts.
#   bash mplus-run.sh                                  dry run (nice -n19)
#   bash mplus-run.sh --run                            real, in the foreground
#   setsid nohup bash mplus-run.sh --run > /mnt/volume2/icsa-2027/mplus/driver.log 2>&1 < /dev/null &      detached, as the other launches
# Options: see `bash mplus-run.sh --help` and mplus-run.md. The head is f1c242a (the frozen head of mplus.md); `--head 09ecc2c` or MPLUS_HEAD=09ecc2c for main's.
# STOP: `touch /mnt/volume2/icsa-2027/mplus/PAUSE` (no further piece starts; the piece in flight finishes). Never kill a call mid-transfer.
set -u
V=/mnt/volume2/icsa-2027; L=$V/launch; HEAD=${MPLUS_HEAD:-f1c242a}
args=("$@")                                                   # the same last-wins reading as argparse: `--head X` and `--head=X` (mplus_run.py allows no abbreviation)
for i in "${!args[@]}"; do
  case "${args[$i]}" in --head=*) HEAD=${args[$i]#--head=};; --head) HEAD=${args[$((i+1))]:-};; esac
done
case "$HEAD" in ''|*[!0-9a-f]*) echo "bad --head '$HEAD' (7 to 12 hex digits)"; exit 2;; esac
[ ${#HEAD} -ge 7 ] && [ ${#HEAD} -le 12 ] || { echo "bad --head '$HEAD' (7 to 12 hex digits)"; exit 2; }
TREE=$V/wt/launch-$HEAD; PY=$TREE/.venv/bin/python
[ -x "$PY" ] || { echo "no $PY"; exit 2; }
run=0; for x in "$@"; do [ "$x" = "--run" ] && run=1; done
[ -f "$L/mplus_run.py" ] || { echo "no $L/mplus_run.py"; exit 2; }
cd "$TREE" || exit 2
if [ $run -eq 1 ]; then exec env PYTHONPATH=. "$PY" "$L/mplus_run.py" --head "$HEAD" "$@"
else exec nice -n19 env PYTHONPATH=. "$PY" "$L/mplus_run.py" --head "$HEAD" "$@"; fi
