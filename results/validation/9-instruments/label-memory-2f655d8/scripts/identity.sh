#!/usr/bin/env bash
L=/mnt/volume2/icsa-2027/scratch-9p/task1; X=/mnt/volume2/icsa-2027/scratch-9p/matrix-old; R=$L/runs; W=/mnt/volume2/icsa-2027/scratch-9p/traced; cap=/mnt/volume2/icsa-2027/bin/memcap
cd /mnt/volume2/icsa-2027/wt/9p-mem; PYTHONPATH=$PWD .venv/bin/python $L/instr_hash.py 2>&1 | tail -2 | tee $L/hash-mem.txt
for h in 9p-shas 9p-mem; do cd /mnt/volume2/icsa-2027/wt/$h; PYTHONPATH=$PWD $cap 12 .venv/bin/python $L/relabel_all.py $X/data-method-window $X/runs $L/relabel-$h.jsonl 2>&1 | tail -2; echo "relabel $h rc=$?"; done
cd $L; sha256sum relabel-9p-shas.jsonl relabel-9p-mem.jsonl; cmp relabel-9p-shas.jsonl relabel-9p-mem.jsonl && echo RELABEL_IDENTICAL || echo RELABEL_DIFFER
cd /mnt/volume2/icsa-2027/wt/9p-mem
id() { PYTHONPATH=$PWD $cap 10 .venv/bin/python $L/identity_real.py "$@" 2>&1 | tail -2 | cut -c1-400; }
id oracle-T-S1 $R/I01__T__S1__qwen__s1/gate_requests.jsonl I01 gate
id oracle-D-S1 $R/I01__D__S1__qwen__s1/gate_requests.jsonl I01 gate
id traced-T $W/T/runs/T__S1__complete/platform/proxy.jsonl I01 proxy
id oracle-T-S2 $R/I43__T__S2__qwen__s1/gate_requests.jsonl I43 gate --every=4
id oracle-D-S2 $R/I48__D__S2__qwen__s1/gate_requests.jsonl I48 gate --every=40
