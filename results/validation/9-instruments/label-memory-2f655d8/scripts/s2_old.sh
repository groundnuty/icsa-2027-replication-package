#!/usr/bin/env bash
wt=$1; tag=$2; cap=$3; L=/mnt/volume2/icsa-2027/scratch-9p/task1; R=$L/runs; W=/mnt/volume2/icsa-2027/scratch-9p/traced
run() { name=$1; o=$2; d=$3; i=$4; lay=$5; shift 5; $L/capped.sh $tag-$name $cap 900 $wt $L/label_one.py $o $d/trace $d/output $d $i --layout $lay --json $L/$tag-$name.json "$@"; grep -E 'STAGE|TOTAL|required' $L/$tag-$name.out | cut -c1-110; grep -v -E 'Timeout|Thread|frozen|wrap.py|^$' $L/$tag-$name.err | tail -3 | cut -c1-110; }
run D-S1-oracle D $R/I01__D__S1__qwen__s1 I01 S1
run D-S2-oracle D $R/I48__D__S2__qwen__s1 I48 S2
run T-S2-oracle T $R/I43__T__S2__qwen__s1 I43 S2
# M: the traced run, with a real S1 oneclient perf log beside it (another run's, I01): the campaign's outside view for M
mkdir -p $R/M-perf/oneclient_perf; cp $R/perf-s1m/s11cal-3496e216-0001-whole_file_skip.S1.M.cold.r2/*.csv $R/M-perf/oneclient_perf/
d=$W/M/runs/M__S1__complete; $L/capped.sh $tag-M-perf $cap 900 $wt $L/label_one.py M $d/trace $d/output $R/M-perf I01 --code $d/agent.py --json $L/$tag-M-perf.json; grep -E 'STAGE|TOTAL' $L/$tag-M-perf.out | cut -c1-110
