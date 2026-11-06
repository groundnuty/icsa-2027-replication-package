#!/usr/bin/env bash
# Fills the transcript scan's private cache AHEAD of the final (lane-layout, #34; science 22:29Z): every `done` S1 attempt of a merged store, one at a time, at the lowest priority.
#   transcriptscan-fill.sh <merged store dir> <cache dir>          (e.g. coding-merged/current  /mnt/volume2/icsa-2027/snap-transcript-cache)
# nice 19, ionice idle, a 4 GiB memory cap, one process. It WAITS while PAUSE_FILE exists (touch it for an interim's heavy stages, remove it after) and stops for good at STOP_BY (default
# 2026-11-06T08:30:00Z). Run it from the driver's loop, like the layout cache's fill; it prints one line of counts: `transcriptscan fill s1_attempts=N hit=H miss=M unreadable=U`.
set -u
export SSH_AUTH_SOCK=
STORE=${1:?merged store dir}; CACHE=${2:?cache dir}
V=/mnt/volume2/icsa-2027
WT=~/work/wt
TREE=${TREE:-$WT/snap-run}
PY=${PY:-$WT/fill-09ecc2c0/.venv/bin/python}
STOP_BY=${STOP_BY:-2026-11-06T08:30:00Z}
PAUSE_FILE=${PAUSE_FILE:-$V/snap-transcript-cache.PAUSE}
umask 077
mkdir -p -m 700 "$CACHE"
cd "$TREE" || exit 2
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 nice -n 19 ionice -c3 "$V/bin/memcap" 4 "$PY" -m snapshot.transcriptscan fill --merged-root "$STORE" --cache "$CACHE" --stop-by "$STOP_BY" --pause-file "$PAUSE_FILE"
