#!/usr/bin/env bash
# Waits for the whole-baseline run; then the cause inputs: whole logs (new real, new stub, old stub) and slices (both heads).
L=/mnt/volume2/icsa-2027/scratch-9p/task1; cap=/mnt/volume2/icsa-2027/bin/memcap
while pgrep -f '[g]en_traced.py T S1 complete_whole_baseline' >/dev/null; do sleep 15; done
tail -1 $L/gen-T-S1-complete_whole_baseline.out | cut -c1-120
one() { h=$1; mode=$2; g=$3; cd /mnt/volume2/icsa-2027/wt/$h; PYTHONPATH=$PWD $cap $g timeout 1800 .venv/bin/python $L/cause_inputs.py $mode $L/cause-$h-$mode.json > $L/cause-$h-$mode.log 2>&1; echo "$h $mode rc=$? $(tail -1 $L/cause-$h-$mode.log | cut -c1-60)"; }
one 9p-mem2 real 6
one 9p-mem2 stub 6
one 9p-shas stub 6
one 9p-mem2 slice 40
one 9p-shas slice 40
cd $L
python3 - <<'PY'
import json
L="/mnt/volume2/icsa-2027/scratch-9p/task1/"
load=lambda n: json.load(open(L+n))
CAUSE=("label","reasons","read_beyond_days","read_beyond_units","read","decoded_not_delivered","dnd_items","delivered_not_decoded","ndd_items","examples","listing_disagrees","unknown_ids","source")
def strip(r): return {k:{f:v[f] for f in CAUSE} for k,v in r.items()}
a,b,c=load("cause-9p-shas-stub.json"),load("cause-9p-mem2-stub.json"),load("cause-9p-mem2-real.json")
print("old stubbed == new stubbed, whole logs:", a==b, len(a), "cases")
print("cause inputs: old stubbed == new real, whole logs:", strip(a)==strip(c))
s,t=load("cause-9p-shas-slice.json"),load("cause-9p-mem2-slice.json")
print("slices, everything incl. fetched and delivered: old == new:", s==t, len(s), "cases")
for k in sorted(c):
    v=c[k]; print(f"  {k}: read_beyond_days {len(v['read_beyond_days'])}, decoded_not_delivered {v['dnd_items']}, delivered_not_decoded {v['ndd_items']}, label {v['label']}")
for k in sorted(t):
    v=t[k]; print(f"  slice {k}: fetched files {v['fetched']['files'] if v['fetched'] else None}, units {v['fetched']['ext']['units'] if v['fetched'] else None}, fetched beyond {v['fetched']['beyond'] if v['fetched'] else None}, read_beyond_days {len(v['read_beyond_days'])}, dnd {v['dnd_items']}, ndd {v['ndd_items']}")
PY
