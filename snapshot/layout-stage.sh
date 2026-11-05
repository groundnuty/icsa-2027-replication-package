#!/usr/bin/env bash
# The layout stage of an interim snapshot (lane-layout, #34; science's request of 5 Nov, comment 6646904218):
#   layout_read per run over BOTH layouts' manifests + the per-run BYPASS count  ->  the H3 reading beside the primary  ->  the own-layout tables (by unit) and the within-environment tables.
#   snapshot-interim-layout.sh <t> <seal dir>        (after the analysis, the coded analysis, and the H3 stage: it reads out-coded/ (else out/), h3/platform_rows.jsonl, M/providers.json)
# Everything it writes is under <seal>/layout/ (sealed, mode 700): layout_read.csv, bypass.csv, bypass_summary.json, counts_by_reason.json, layout_read.meta.json, h3-own/, own-only/,
# env-vm/, env-hpc/ ({tables,inputs,units.csv,units_by_model.csv,...}), environments/beside/, environment_units.json.
# stdout is totals and seconds only (no value, no count by option, no count of units or runs left out); the one line about bypass says only whether it happened: `it_happened=no|yes`.
# The sealed files are not read here. Exit 0 only when every sub-stage ran clean; a sub-stage that fails does not
# hide the ones that do not depend on it (the H3 reading and the own-only tables need layout_read.csv, so they are skipped, rc 9, when `read` failed).
# A snapshot is never overwritten: if <seal>/layout/ already holds one of these, the sub-stage refuses (rc 2): move it aside.
set -u
export SSH_AUTH_SOCK=
T=${1:?t}; SEAL=${2:?seal dir}
V=/mnt/volume2/icsa-2027
WT=~/work/wt
TREE=${TREE:-$WT/snap-run}                         # 09ecc2c0 + snapshot/ of main (layoutread.py and layoutown.py must be in it)
H3_TREE=${H3_TREE:-$WT/snap-interim}               # the tree the H3 stage's pinned measure runs from (the pin is a hash: any tree that matches runs)
PY=${PY:-$WT/fill-09ecc2c0/.venv/bin/python}
PIN=${PIN:-$V/snap-h3/pin.txt}
AUDIT_ROOT=${AUDIT_ROOT:-$V/snap-h3}
MEMCAP=${MEMCAP:-8}
LAYOUT_CACHE=${LAYOUT_CACHE:-}                                    # a directory (mode 700, sealed): the per-run evidence cache; empty: no cache
LAYOUT_JOBS=${LAYOUT_JOBS:-4}                                     # layout_read: worker processes (the logs of a snapshot are some GB)
PROVIDER_TABLE=${PROVIDER_TABLE:-$V/lane-snap4/providers.tsv}     # a `site_a` third column is HPC
OWN_VARIANTS=${OWN_VARIANTS:-own-only,env-vm,env-hpc,bytes-measured}   # one analysis each, run in parallel (about 2-3 min); own-only-strict is off unless science asks
OUT=$SEAL/layout
mkdir -p -m 700 "$OUT"
umask 077
STAGES=$OUT/stages.jsonl
memgate() {
  local deadline=$(( $(date +%s) + 600 )) a
  while :; do
    a=$(awk '/MemAvailable/{printf "%d", $2/1048576}' /proc/meminfo)
    [ "$a" -ge $(( MEMCAP + 4 )) ] && return 0
    [ "$(date +%s)" -lt "$deadline" ] || { echo "memgate: MemAvailable ${a}GiB < $(( MEMCAP + 4 ))GiB for 600s: refused"; return 75; }
    sleep 20
  done
}
sub() {
  local name=$1; shift
  local s0 s1 rc
  s0=$(date +%s.%N)
  "$@" > "$OUT/$name.out" 2> "$OUT/$name.err" < /dev/null; rc=$?
  s1=$(date +%s.%N)
  python3 -I -c 'import json,sys; n,a,b,rc=sys.argv[1:5]; print(json.dumps({"substage":n,"seconds":round(float(b)-float(a),1),"rc":int(rc)}))' "$name" "$s0" "$s1" "$rc" >> "$STAGES"
  echo "layout $name rc=$rc seconds=$(python3 -I -c "print(round($s1-$s0,1))") $(tail -n 1 "$OUT/$name.out" | cut -c1-160)"
  return $rc
}
step() { memgate || return 75; ( cd "$TREE" && PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 ICSA_DATA=$V nice -n 10 "$V/bin/memcap" "$MEMCAP" "$PY" -m snapshot.layoutread "$@" ); }
rc_all=0
CACHE=(); [ -z "${LAYOUT_CACHE:-}" ] || CACHE=(--cache "$LAYOUT_CACHE")      # the per-run evidence cache (snapshot/layoutcache.py): a run found in it is not read again
sub read step read "$SEAL" --audit-root "$AUDIT_ROOT" --jobs "$LAYOUT_JOBS" --providers-table "$PROVIDER_TABLE" "${CACHE[@]}" || rc_all=1
if [ ! -s "$OUT/layout_read.csv" ]; then
  echo "layout: layout_read.csv does not exist: the H3 reading and the own-only tables are not run"; exit 9
fi
sub h3 step h3 "$SEAL" --tree "$H3_TREE" --pin "$PIN" || rc_all=1
H3T=(); [ -z "${H3_TABLE:-}" ] || H3T=(--h3-table "$H3_TABLE")
sub own step own "$SEAL" --variants "$OWN_VARIANTS" "${H3T[@]}" || rc_all=1
exit $rc_all
