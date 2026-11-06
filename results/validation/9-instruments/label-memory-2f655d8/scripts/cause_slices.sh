#!/usr/bin/env bash
L=/mnt/volume2/icsa-2027/scratch-9p/task1; cap=/mnt/volume2/icsa-2027/bin/memcap
one() { h=$1; cd /mnt/volume2/icsa-2027/wt/$h; PYTHONPATH=$PWD $cap 30 timeout 3400 .venv/bin/python $L/cause_inputs.py slice $L/cause-$h-slice.json > $L/cause-$h-slice.log 2>&1; echo "$h slice rc=$? $(tail -1 $L/cause-$h-slice.log | cut -c1-60)"; }
rm -f $L/cause-9p-mem2-slice.json $L/cause-9p-shas-slice.json
one 9p-mem2; one 9p-shas
cd $L; python3 - <<'PY'
import json
L="/mnt/volume2/icsa-2027/scratch-9p/task1/"
s,t=json.load(open(L+"cause-9p-shas-slice.json")),json.load(open(L+"cause-9p-mem2-slice.json"))
print("slices, everything incl. fetched and delivered: old == new:", s==t, len(s), "cases")
for k in sorted(t):
    v=t[k]; print(f"  {k}: fetched files {v['fetched']['files']}, units {v['fetched']['ext']['units']}, beyond {v['fetched']['beyond']}, fetched beyond_days {len(v['fetched']['beyond_days'])}, read_beyond_days {len(v['read_beyond_days'])}, dnd {v['dnd_items']}, ndd {v['ndd_items']}")
PY
