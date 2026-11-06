#!/usr/bin/env bash
# Every measured run at one head, one after another, under a small cap: per option, index load apart from labelling.
wt=$1; tag=$2; cap=$3; L=/mnt/volume2/icsa-2027/scratch-9p/task1; R=$L/runs; W=/mnt/volume2/icsa-2027/scratch-9p/traced
run() { name=$1; shift; $L/capped.sh $tag-$name $cap 900 $wt $L/label_one.py "$@" --json $L/$tag-$name.json > /dev/null; echo "== $name"; grep -E 'STAGE (load|label)|TOTAL' $L/$tag-$name.out | cut -c1-110; }
tr() { o=$1; name=$2; shift 2; d=$W/$o/runs/${o}__S1__complete; run $name $o $d/trace $d/output $d/platform I01 --code $d/agent.py "$@"; }
tr T traced-T
tr D traced-D --root $W/D/runs/D__S1__complete/downloads
tr M traced-M
tr M traced-M-strace --root /mnt/volume2/icsa-2027
d=$W/M/runs/M__S1__complete; run traced-M-perf M $d/trace $d/output $R/M-perf I01 --code $d/agent.py
# K_RUNS: "run-dir instance" pairs, one per line, given from outside: K is a blind test, so its case ids are never in the repository
n=0; while read -r r i; do [ -n "$r" ] || continue; n=$((n+1)); c=$r/cells/cells.jsonl; [ -f $c ] || c=$r/code_cells.json; run K-run-$n M $r/trace $r/output $r $i --code $c; done <<< "${K_RUNS:-}"
o() { name=$1; opt=$2; r=$R/$3; i=$4; lay=$5; run $name $opt $r/trace $r/output $r $i --layout $lay; }
o oracle-T-S1 T I01__T__S1__qwen__s1 I01 S1
o oracle-D-S1 D I01__D__S1__qwen__s1 I01 S1
o oracle-T-S2 T I43__T__S2__qwen__s1 I43 S2
o oracle-D-S2 D I48__D__S2__qwen__s1 I48 S2
