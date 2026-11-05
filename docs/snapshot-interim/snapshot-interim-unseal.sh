#!/usr/bin/env bash
# The coding decisions of an interim snapshot (science's ruling, #34 22:55Z: `report.py --unseal` INSIDE the snapshot path, as a mechanical step, for every interim and the final).
#   snapshot-interim-unseal.sh <t> <seal dir>
# Everything it writes is under <seal>/inspection (decisions, population, report: sealed, mode 700) and two files in <seal>/frozen: inspection-labels.jsonl and inspection-coverage.jsonl,
# which the snapshot's SECOND analysis takes (`--inspection-labels`, `--inspection-coverage`). NOTHING is written in the coders' work directory, plan or sealed answers, and nothing is printed
# but sub-stage names, seconds and return codes: decisions are never shown. Inputs, as lane-code76 gave them (4 Nov): the plan /mnt/volume2/icsa-2027/inspection-coders/plan.json, the sealed
# answers /mnt/volume2/icsa-2027/snapshots/coding/sealed (read), the coders' work directory (read), and the population built from THIS cut's own store and pipeline output, by the coders' own
# tree (a tree of origin/main) and interpreter. A fresh output directory per interim, read only after the command has exited.
#   gate        cp <coders' work>/quota/gate.json -> <seal>/work/quota/   (the gate's state, frozen into our dir: report reads <seal>/work, never the coders' work dir)
#   population  python -m icsa.inspection.population --campaign-root <cut> --pipeline-out <out/pipeline> --out <seal>/inspection/population.jsonl
#   report      python -m icsa.inspection.report --pair-plan PLAN --sealed SEALED --unseal --population POP --work <seal>/work --out <seal>/inspection     -> decisions.json
#   labels      inspection-coders/write_labels.py --decisions decisions.json --out <seal>/inspection/labels.jsonl                      (lane-code76's, final format)
#   filter      filter_labels.py: the labels of runs in THIS cut only (the analysis refuses a label for a run that is not in it)
#   coverage    python -m icsa.inspection.coverage --population POP --decisions decisions.json --out <seal>/inspection/coverage.jsonl
# then labels and coverage are copied to <seal>/frozen/ for the second analysis. (Commands as lane-code76 gave them, 4 Nov 23:05Z; nothing in them writes under inspection-coders/.)
# Exit 0 only when all four ran clean. A failure leaves no labels file, the second analysis is skipped, and cell_counts.csv says needs_unseal.
set -u
T=${1:?t}; SEAL=${2:?seal dir}
V=/mnt/volume2/icsa-2027
CT=${CODERS_TREE:-$V/inspection-coders/tree-52ddcad8}
PYC=${CODERS_PY:-$CT/.venv/bin/python}
PLAN=${CODERS_PLAN:-$V/inspection-coders/plan.json}
SEALED=${CODERS_SEALED:-$V/snapshots/coding/sealed}
WORK=${CODERS_WORK:-$V/inspection-coders/work}             # READ only, and only for the gate's own file (gate.json), copied into the seal first
INS=$SEAL/inspection
umask 077
mkdir -p -m 700 "$INS" "$SEAL/frozen"
STAGES=$INS/stages.jsonl
case "$INS" in "$SEAL"/*) ;; *) echo "unseal: output outside the seal: refused" >&2; exit 2;; esac
case "$INS" in "$WORK"*|"$V/inspection-coders"*|"$SEALED"*) echo "unseal: output inside the coders' directories: refused" >&2; exit 2;; esac
memgate() {
  local deadline=$(( $(date +%s) + 600 )) a
  while :; do
    a=$(awk '/MemAvailable/{printf "%d", $2/1048576}' /proc/meminfo)
    [ "$a" -ge 8 ] && return 0
    [ "$(date +%s)" -lt "$deadline" ] || { echo "memgate: MemAvailable ${a}GiB < 8GiB for 600s: refused"; return 75; }
    sleep 20
  done
}
sub() {
  local name=$1; shift
  local s0 s1 rc
  s0=$(date +%s.%N)
  "$@" > "$INS/$name.out" 2> "$INS/$name.err" < /dev/null; rc=$?
  s1=$(date +%s.%N)
  python3 -I -c 'import json,sys; n,a,b,rc=sys.argv[1:5]; print(json.dumps({"substage":n,"seconds":round(float(b)-float(a),1),"rc":int(rc)}))' "$name" "$s0" "$s1" "$rc" >> "$STAGES"
  echo "unseal $name rc=$rc seconds=$(python3 -I -c "print(round($s1-$s0,1))")"
  return $rc
}
run_c() { memgate || return 75; ( cd "$CT" && PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 nice -n 10 "$V/bin/memcap" 4 "$PYC" "$@" ); }
rm -f "$SEAL/frozen/inspection-labels.jsonl" "$SEAL/frozen/inspection-coverage.jsonl"
rc=0
gate_copy() { mkdir -p -m 700 "$SEAL/work/quota" && cp -f "$WORK/quota/gate.json" "$SEAL/work/quota/gate.json"; }
sub gate gate_copy || rc=1
if [ $rc -eq 0 ] && [ -n "${CODERS_POPULATION:-}" ]; then      # a DRY RUN on lane-code76's rehearsal world (fake plan, fake sealed answers): its own population, never a study run
  sub population cp -f "$CODERS_POPULATION" "$INS/population.jsonl" || rc=1
elif [ $rc -eq 0 ]; then
  sub population run_c -m icsa.inspection.population --campaign-root "$SEAL/out/work/cut" --pipeline-out "$SEAL/out/pipeline" --out "$INS/population.jsonl" || rc=1
fi
if [ $rc -eq 0 ]; then       # its one stdout line is the gate status (an outcome): sealed in $INS/report.out
  sub report run_c -m icsa.inspection.report --pair-plan "$PLAN" --sealed "$SEALED" --unseal --population "$INS/population.jsonl" --work "$SEAL/work" --out "$INS" || rc=1
fi
# lane-code76 (science item 5, 5 Nov 12:19Z): pair_kappa.csv / pair_kappa.json beside decisions.json, from the same decisions; a side table, so it never fails the unseal (its one line stays in the sealed pair_kappa.out)
pair_kappa_run() { TREE="$CT" run_c "$V/inspection-coders/pair_kappa.py" --decisions "$INS/decisions.json" --out-dir "$INS"; }
if [ $rc -eq 0 ] && [ -f "$INS/decisions.json" ]; then sub pair_kappa pair_kappa_run || true; fi
if [ $rc -eq 0 ]; then
  sub labels run_c "$V/inspection-coders/write_labels.py" --decisions "$INS/decisions.json" --out "$INS/labels.jsonl" || rc=1
fi
if [ $rc -eq 0 ]; then
  sub coverage run_c -m icsa.inspection.coverage --population "$INS/population.jsonl" --decisions "$INS/decisions.json" --out "$INS/coverage.jsonl" || rc=1
fi
if [ $rc -eq 0 ]; then       # only the labels of runs in THIS cut go to the analysis (apply() refuses a label for no scored run); the dropped count is in filter.out and the report
  sub filter python3 -I "$V/launch/filter_labels.py" "$SEAL/out/pipeline/scored_rows.jsonl" "$INS/labels.jsonl" "$SEAL/frozen/inspection-labels.jsonl" || rc=1
fi
if [ $rc -eq 0 ]; then
  cp -f "$INS/coverage.jsonl" "$SEAL/frozen/inspection-coverage.jsonl" || rc=1
fi
[ $rc -eq 0 ] || { rm -f "$SEAL/frozen/inspection-labels.jsonl" "$SEAL/frozen/inspection-coverage.jsonl"; echo "unseal: a sub-stage failed: no labels file left (logs in inspection/*.err, sealed)"; }
exit $rc
