#!/usr/bin/env bash
# Label the traced T, D and M S1 runs at the code of $1 (worktree), one 60 GiB job at a time.
wt=$1; tag=$2; L=/mnt/volume2/icsa-2027/scratch-9p/task1; W=/mnt/volume2/icsa-2027/scratch-9p/traced
run() { o=$1; name=$2; shift 2; d=$W/$o/runs/${o}__S1__complete; $L/capped.sh $tag-$name 60 1800 $wt $L/label_one.py $o $d/trace $d/output $d/platform I01 --code $d/agent.py --json $L/$tag-$name.json "$@"; grep -E 'STAGE|TOTAL' $L/$tag-$name.out | cut -c1-110; }
run M M-prod
run M M-strace --root /mnt/volume2/icsa-2027
run T T
run D D --root $W/D/runs/D__S1__complete/downloads
