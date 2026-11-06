#!/usr/bin/env bash
# Real-tracer runs on I01's real files through the local server, stopped before labelling; four at a time, each capped.
L=/mnt/volume2/icsa-2027/scratch-9p/task1; W=/mnt/volume2/icsa-2027/scratch-9p/traced
printf '%s\n' "T S1 skip" "D S1 skip" "M S1 skip" "T S1 complete_whole_baseline" "D S1 complete_whole_baseline" "T S2 skip" "D S2 skip" "M S2 skip" "M S2 complete" "T S2 complete" |
xargs -P 4 -I{} bash -c 'set -- {}; $0/capped.sh gen-$1-$2-$3 16 1800 9p-mem2 $0/gen_traced.py $1 $2 $3 I01 /mnt/volume2/icsa-2027/scratch-9p/traced/$1 2>&1 | cut -c1-120' $L > /dev/null
for f in $L/gen-*-S?-*.out; do echo "$(basename $f): $(tail -1 $f | cut -c1-110)"; done
