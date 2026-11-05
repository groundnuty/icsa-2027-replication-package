#!/usr/bin/env bash
# The H3 stage of an interim snapshot (lane-snap, #34): extract on every audit store (refreshed copy, incremental), the platform rows joined into one file by the merge's
# owners, then the PINNED measure over the snapshot's scored rows.   snapshot-interim-h3.sh <t> <seal dir>
#   extract_all  h3-loop.sh once: site_g (main's M audit) and each B provider, serial, under the loop's lock
#   join         h3_join.py: each run's platform row from its OWNER's store (the merge's providers.json), one file
#   measure      python -m icsa.faults.mainaudit measure --pin <the pin> --scored out/pipeline/scored_rows.jsonl --platform <joined> --out <seal>/h3/measure
# The pin is the lead's (launch/h3-measure-pin.json, pin_sha256), written once as the hex-only file the measure reads; the measure refuses (exit 3) unless the code hashes to it.
# Everything it writes is under <seal>/h3 (sealed). stdout is counts and seconds only; the measure writes counts.json, self_report.json, record.json and record.csv, never a value
# to the terminal. Exit 0 only when all three sub-stages ran clean; a store whose extract did not run (main without its inputs) makes extract_all fail, and the join and the
# measure still run on what exists, so one broken store never hides the rest (the measure counts runs without a platform row).
set -u
export SSH_AUTH_SOCK=
T=${1:?t}; SEAL=${2:?seal dir}
V=/mnt/volume2/icsa-2027
WT=~/work/wt
H3=${H3:-$V/snap-h3}
TREE=${TREE:-$WT/snap-interim}
PY=${PY:-$WT/fill-09ecc2c0/.venv/bin/python}
. "$V/launch/lib-providers.sh"; load_providers
OUT=$SEAL/h3
STAGES=$OUT/stages.jsonl; [ "${H3_MEASURE_ONLY:-0}" != 1 ] || STAGES=$OUT/stages.measure-only.jsonl
mkdir -p -m 700 "$OUT"
umask 077
PIN=$H3/pin.txt
if [ ! -s "$PIN" ]; then
  python3 -I -c "import json,re,sys; p=json.load(open('$V/launch/h3-measure-pin.json'))['pin_sha256']; assert re.fullmatch('[0-9a-f]{64}', p); print(p)" > "$PIN.tmp" && mv "$PIN.tmp" "$PIN" || { echo "h3: cannot derive the pin file" >&2; exit 3; }
fi
# the join and the measure are heavy enough to matter on this host (rows held in memory): a MemAvailable gate (wait up to 10 min, then refuse), nice, and a memcap
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
  "$@" > "$OUT/$name.out" 2> "$OUT/$name.err" < /dev/null; rc=$?
  s1=$(date +%s.%N)
  python3 -I -c 'import json,sys; n,a,b,rc=sys.argv[1:5]; print(json.dumps({"substage":n,"seconds":round(float(b)-float(a),1),"rc":int(rc)}))' "$name" "$s0" "$s1" "$rc" >> "$STAGES"
  echo "h3 $name rc=$rc seconds=$(python3 -I -c "print(round($s1-$s0,1))")"
  return $rc
}
rc_all=0
# An incremental extract pass costs the audit phase (about 35 min, the whole capture is streamed whenever one attempt is pending) plus the switched-on phase, so a snapshot does NOT start one:
# the extract loop (h3-loop.sh, passes back to back) keeps every store warm, and this stage takes each store's last COMPLETED pass, reports how old it is against t, and fails (exit 7 of the driver)
# only when a store's last pass is older than H3_MAX_STALE_S (90 min) before t or does not exist. H3_EXTRACT_MODE=pass restores a bounded pass (H3_PASS_TIMEOUT_S, default 900 s) first.
MODE=${H3_EXTRACT_MODE:-lastpass}
# the fixed snapshot's catch-up pass (started by the driver after the freeze): wait for it until its deadline, then take each store's last COMPLETED pass as usual
if [ -n "${H3_CATCHUP_PID:-}" ]; then
  cw0=$(date +%s)
  while kill -0 "$H3_CATCHUP_PID" 2>/dev/null && [ "$(date +%s)" -lt "${H3_CATCHUP_DEADLINE:-0}" ]; do sleep 20; done
  if kill -0 "$H3_CATCHUP_PID" 2>/dev/null; then echo "h3 catch-up: NOT finished at its deadline (waited $(( $(date +%s) - cw0 )) s): the stores' last completed passes stand"; else echo "h3 catch-up: finished (waited $(( $(date +%s) - cw0 )) s); $(tail -n 1 "$SEAL/logs/h3_catchup.out" 2>/dev/null | cut -c1-120)"; fi
fi
TS_T=$(date -u -d "$T" +%s)
stale_check() {
  local n f m bad=0 out=""
  for n in site_g $PROVIDERS; do
    f=$H3/$n/platform_rows.jsonl
    if [ "$n" != site_g ] && [ ! -d "$V/provider-audit/$n" ]; then out+=" $n=no-audit-store"; continue; fi      # no audit source for it yet: reported here, and its runs count as no_platform_row in the measure
    if [ -f "$f" ]; then m=$(stat -c %Y "$f"); out+=" $n=$(( m - TS_T ))"; [ $(( TS_T - m )) -le "${H3_MAX_STALE_S:-5400}" ] || { bad=1; out+="(STALE)"; }
    else out+=" $n=none"; bad=1; fi
  done
  echo "last completed extract pass vs t (s):$out"
  return $bad
}
# which monitor file each provider's last extract pass used and its first real sample (lane-site_aaudit's request): one file in the seal, times only
python3 -I - "$H3" "$OUT/mon_used.json" <<'PYU' 2>/dev/null || true
import glob, json, os, sys
out = {}
for f in sorted(glob.glob(os.path.join(sys.argv[1], "*", "mon.used.json"))):
    try:
        out[os.path.basename(os.path.dirname(f))] = json.load(open(f))
    except Exception:
        pass
json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
PYU
if [ "${H3_MEASURE_ONLY:-0}" = 1 ]; then
  echo "h3: measure only (the extract check and the join are not repeated)"
elif [ "${H3_SKIP_EXTRACT:-0}" = 1 ]; then      # a test of the join and the measure on the stores as they are; never set for a snapshot
  echo "h3: extract_all SKIPPED (H3_SKIP_EXTRACT=1)"; echo '{"substage":"extract_all","skipped":true}' >> "$STAGES"; rc_all=1
elif [ "$MODE" = pass ]; then
  sub extract_all env LOCK_WAIT_S="${H3_LOCK_WAIT_S:-600}" PASS_TIMEOUT_S="${H3_PASS_TIMEOUT_S:-900}" bash "$V/launch/h3-loop.sh" once site_g $PROVIDERS || rc_all=1
  tail -n 8 "$H3/logs/h3-loop.log" | sed 's/^/h3 loop: /' | cut -c1-200
else
  sub extract_check stale_check || rc_all=1
  echo "h3 $(tail -n 1 "$OUT/extract_check.out")"
fi
# ---- the measure's truth is the ANALYSIS label, inspection included (science, #34 00:46Z; amendment 42(a)): the pipeline's scored_rows.jsonl is written before the analysis applies the coders'
# decisions, so with the labels frozen in the seal the rows are rebuilt with the same frozen functions (scored_coded.py) and handed to `measure --scored` (an argument, not part of the pin).
# H3_MEASURE_ONLY=1: re-run the measure alone on an existing seal; the old h3/measure is moved to h3/measure.before-coded first (never overwritten, refused if that exists).
LABELS=$SEAL/frozen/inspection-labels.jsonl; COV=$SEAL/frozen/inspection-coverage.jsonl
SCORED_IN=$SEAL/out/pipeline/scored_rows.jsonl; [ ! -f "$SEAL/out-coded/pipeline/scored_rows.jsonl" ] || SCORED_IN=$SEAL/out-coded/pipeline/scored_rows.jsonl
if [ "${H3_MEASURE_ONLY:-0}" = 1 ]; then
  if [ -d "$OUT/measure" ]; then
    [ ! -e "$OUT/measure.before-coded" ] || { echo "h3: $OUT/measure.before-coded exists: refused (never overwritten)"; exit 2; }
    mv "$OUT/measure" "$OUT/measure.before-coded"
  fi
else
STORES=(--store "site_g=$H3/site_g"); for p in $PROVIDERS; do STORES+=(--store "$p=$H3/$p"); done
joinrun() { memgate || return 75; nice -n 10 "$V/bin/memcap" 2 "$PY" "$V/launch/h3_join.py" "$@"; }
sub join joinrun --providers "$SEAL/M/providers.json" "${STORES[@]}" --out "$OUT/platform_rows.jsonl" || rc_all=1
echo "h3 join: $(tail -n 1 "$OUT/join.out")"
fi
if [ -f "$SCORED_IN" ] && [ -f "$OUT/platform_rows.jsonl" ]; then
  if [ -s "$LABELS" ] && [ -s "$COV" ]; then
    SRC_LABEL="out-coded (inspection applied)"
    codedrows() { memgate || return 75; ( cd "$TREE" && PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 ICSA_DATA=$V nice -n 10 "$V/bin/memcap" 2 "$PY" "$V/launch/scored_coded.py" "$SCORED_IN" "$LABELS" "$COV" "$OUT/scored_rows_coded.jsonl" "$SEAL/out/work/cut/state.sqlite" ); }
    sub scored_coded codedrows || rc_all=1
    SCORED=$OUT/scored_rows_coded.jsonl
    [ -f "$SCORED" ] || { echo "h3: the coded rows could not be built: measure not run on uncoded truth"; exit 7; }
  else
    SRC_LABEL="out (NO inspection: the coders' decisions were not in this snapshot)"; SCORED=$SCORED_IN; rc_all=1
  fi
  # the per-day truth (lane-h3b's relabel on .16, copied into the seal by daytruth_pull.sh) enables the stricter readings (i) and (ii); the measure refuses a file made by other labeller code
  # than this tree's: then it is run again WITHOUT it, the refused output is kept beside (measure.refused-day-truth) and the label source says so. No directory: no_day_truth, as before.
  DTARG=(); DTNOTE="no per-day truth copied into this seal"
  [ ! -d "$SEAL/frozen/daytruth" ] || { DTARG=(--day-truth "$SEAL/frozen/daytruth"); DTNOTE="per-day truth of the last completed pass: $(cut -c1-120 "$SEAL/frozen/daytruth.pass" 2>/dev/null)"; }
  measure() ( cd "$TREE" && PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 nice -n 10 "$V/bin/memcap" 4 "$PY" -m icsa.faults.mainaudit measure --pin "$PIN" --scored "$SCORED" \
        --platform "$OUT/platform_rows.jsonl" --out "$OUT/measure" "${DTARG[@]}" )
  measure_gated() { memgate || return 75; measure; }
  sub measure measure_gated; mrc=$?
  if [ $mrc -ne 0 ] && [ ${#DTARG[@]} -gt 0 ]; then
    rm -rf "$OUT/measure.refused-day-truth"; mv "$OUT/measure" "$OUT/measure.refused-day-truth" 2>/dev/null; cp "$OUT/measure.out" "$OUT/measure.refused-day-truth.out" 2>/dev/null
    DTARG=(); DTNOTE="the per-day truth was REFUSED by the measure (rc=$mrc: see measure.refused-day-truth.out); run without it"
    sub measure measure_gated; mrc=$?
  fi
  [ $mrc -eq 0 ] || rc_all=1
  # the label source goes into counts.json (an added top-level key, written here AFTER the pinned code wrote the file; the pinned code and its other bytes are untouched) and beside it
  python3 -I - "$OUT/measure" "$SRC_LABEL" "$SCORED" "$DTNOTE" <<'PY'
import json, os, sys, tempfile
d, src, scored = sys.argv[1:4]
info = {"label_source": src, "day_truth": sys.argv[4], "scored_rows_file": os.path.basename(scored), "note": "added by the snapshot driver after the pinned measure ran; the measure's code and its other outputs are unchanged"}
json.dump(info, open(os.path.join(d, "label_source.json"), "w"), indent=1)
p = os.path.join(d, "counts.json")
if os.path.isfile(p):
    c = json.load(open(p)); c["label_source"] = src; c["day_truth"] = sys.argv[4]
    fd, tmp = tempfile.mkstemp(dir=d); os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as fh: json.dump(c, fh, indent=1, sort_keys=True)
    os.replace(tmp, p)
PY
  # the join's account (whole-cut counts: scored rows, platform rows, runs without a platform row, platform rows without a scored row, attempt mismatches) is the only part printed
  python3 -I - "$OUT/measure.out" <<'PY'
import json, re, sys
t = open(sys.argv[1]).read()
m = re.search(r"'join': (\{[^}]*\})", t) or re.search(r'"join": (\{[^}]*\})', t)
print("h3 measure join: " + (m.group(1) if m else "(no account on stdout; see measure.out, sealed)"))
PY
  echo "h3 measure label source: $SRC_LABEL"
else
  echo "h3: measure not run (no scored rows or no platform rows)"; rc_all=1
fi
exit $rc_all
