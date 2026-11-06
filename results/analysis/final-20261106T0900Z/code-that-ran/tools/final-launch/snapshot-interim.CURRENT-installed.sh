#!/usr/bin/env bash
# The interim snapshot, the FULL path, every stage timed (lane-snap, #34; science 4 Nov 18:49Z):
#   freeze the mirrors at t -> merge main's store with B's -> cut at t - cap -> pipeline assemble (each provider's own cache and index) -> analysis -> H3 measure
#   snapshot-interim.sh <t, ISO UTC>        e.g. 2026-11-05T00:00:00Z        (the cut is t - CAP_S: 29400 s = 490 min -> 15:50Z for 00:00Z)
# Outputs: $SNAPS/interim-<t>/ (mode 700, SEALED: read by no one but the pipeline): frozen/ (the stores as frozen), M/ (the merged root), out/ (the snapshot's own
# --out: cut, pipeline, tables, SNAPSHOT.json), h3/, logs/, stages.jsonl, timings.json.
# The terminal gets ONLY counts and timings: the lines `snapshot` and `bmerge` print for the purpose (whole-cut counts), stage seconds, return codes. No score,
# label or outcome by option is printed, and nothing under out/ is read here. --final "$FINAL" always: the fixed cut (6 Nov 00:00Z) is the lead's own run.
# Choices that science may see (stated, overridable by environment): NO_OUTCOME=as-exhausted (the final's rule, so the path is the final's), MAX_MISSES unset
# (pcache's own limit, max(20, 10%) of the runs: a cold cache REFUSES rather than spending hours; MAX_MISSES=-1 lifts it), overhead/fidelity/inspection 'none'.
set -u
export SSH_AUTH_SOCK=
V=/mnt/volume2/icsa-2027
WT=~/work/wt
TREE=${TREE:-$WT/snap-run}                         # 09ecc2c0 (the cache key's tree) + main's snapshot/: runs cut, assemble, analysis
CAMPAIGN_TREE=${CAMPAIGN_TREE:-$WT/fill-09ecc2c0}  # the campaign's code tree: the code check compares the running icsa files with it, byte for byte
PY=${PY:-$CAMPAIGN_TREE/.venv/bin/python}          # the interpreter is in the cache key
SNAPS=${SNAPS:-$V/snapshots}
SNAP_B=${SNAP_B:-$V/snap-b}
IDX_B=${IDX_B:-$V/snap-b-index}
CACHE_B=${CACHE_B:-$V/snap-b-cache}
CACHE_MAIN=${CACHE_MAIN:-$V/pilot-coding/private/pcache-09ecc2c0}
MAIN_MIRROR=${MAIN_MIRROR:-$V/coding-mirror}
CAP_S=${CAP_S:-29400}
NO_OUTCOME=${NO_OUTCOME:-as-exhausted}
FINAL=${FINAL:-false}                              # `true` only for the paper's fixed snapshot (snapshot/cut.py refuses it for any other t or no-outcome); the scheduler sets it for the final entry alone
SEAL_PREFIX=${SEAL_PREFIX:-interim-}               # `final-` for the fixed snapshot
JOBS=${JOBS:-8}                                       # 8 workers from the 12:00Z interim (the fixed snapshot rehearsal at 8: analyse 612 s against 689 s at 4; pcache keys the per-run limit, which is 8 GiB for any count)
WORKER_GIB=${WORKER_GIB:-8}
MEMCAP=${MEMCAP:-16}
# The fixed snapshot's budget rules (also switchable for a rehearsal: FINAL_MODE=true with FINAL=false): analysis at 8 workers and a 24 GiB cgroup (pcache's per-run limit is the same for any job count at
# worker-gib 8), the loops that are not needed after the freeze stopped, the unseal not before the coders stop, the primary report written before the layout stage, the layout stage time-boxed.
FINAL_MODE=${FINAL_MODE:-$FINAL}
[ "$FINAL_MODE" != true ] || export REPLAY_JOBS=${REPLAY_JOBS:-25695605} REPLAY_FINAL_JOBS=${REPLAY_FINAL_JOBS:-25695605}      # the replay holder jobs of the final and the rerun: hpc-3 only (the small holders end 11:25Z; hpc-4 is the artifact build node; hpc-5 25695758 hit the Slurm step limit 6 Nov 06:02Z). The stage picks REPLAY_FINAL_JOBS when the seal is final, REPLAY_JOBS otherwise
[ "$FINAL_MODE" != true ] || { JOBS=${JOBS_FINAL:-8}; MEMCAP=${MEMCAP_FINAL:-24}; }
OVERHEAD=${OVERHEAD:-none}; FIDELITY_ROWS=${FIDELITY_ROWS:-none}; INSPECTION=${INSPECTION:-none}
H3_TABLE=${H3_TABLE:-}                             # fault calibration's h3_table.csv (with FIDELITY_ROWS = its adapter_rows.jsonl): the fault-injection fidelity exhibit's verdicts; unset: the exhibit says tested=False
FREEZE_WAIT_S=${FREEZE_WAIT_S:-1500}               # how long to wait for main's mirror loop to fetch once after t
# the transcript scan (lane-layout, science 22:29Z): the layout stage's LAST, soft sub-stage reads this cache (filled ahead by lane-snap6/scan-fill-loop.sh); the fill waits while the PAUSE file exists
export SCAN_CACHE=${SCAN_CACHE:-$V/snap-transcript-cache}; SCAN_PAUSE=$V/snap-transcript-cache.PAUSE
H3=${H3:-$V/launch/snapshot-interim-h3.sh}         # the H3 stage, if present and executable: `H3 <t> <seal dir>`; its stdout is sealed, its rc and seconds are timed
. "$V/launch/lib-providers.sh"; load_providers
export PROVIDERS                                    # the H3 stage and the mirrors script read the same list
case "$FINAL" in true|false) ;; *) echo "snapshot-interim: FINAL must be true or false" >&2; exit 64;; esac
T=${1:-}
[ -n "$T" ] || { echo "usage: $0 <t ISO UTC>" >&2; exit 64; }
case "$T" in ????-??-??T??:??:??Z) ;; *) echo "snapshot-interim: t must look like 2026-11-05T00:00:00Z" >&2; exit 64;; esac
TS=$(date -u -d "$T" +%s) || exit 64
[ "$TS" -le "$(date -u +%s)" ] || { echo "snapshot-interim: t is in the future" >&2; exit 64; }
TAG=$(date -u -d "$T" +%Y%m%dT%H%MZ)
SEAL=$SNAPS/$SEAL_PREFIX$TAG${TAG_SUFFIX:-}      # TAG_SUFFIX=-check-cap600 names a PIPELINE CHECK (a short CAP_S: never a snapshot, never reported as one)
if [ -n "${REFREEZE_FROM:-}" ]; then SEAL=$SNAPS/$(basename "$REFREEZE_FROM" | sed 's/-r[0-9]*$//')${TAG_SUFFIX:-}; fi      # a re-freeze rerun is named after the seal it re-freezes
[ ! -e "$SEAL" ] || { echo "snapshot-interim: $SEAL exists: a snapshot is never overwritten (move it aside)" >&2; exit 65; }
umask 077
mkdir -p -m 700 "$SNAPS" && mkdir -m 700 "$SEAL" && mkdir -m 700 "$SEAL/logs" "$SEAL/frozen" "$SEAL/h3" || exit 65
STAGES=$SEAL/stages.jsonl
# RERUN MODE (lane-snap6): RESUME_FROM=<a sealed dir of the same t>, TAG_SUFFIX=-r1 (a new dir, never an overwrite). The freeze, the merge, the final's pulls/quiesce/catch-up, the fault-calibration pull and the unseal
# are NOT run again: frozen/, M/, inspection/ and coder_replay/ of that seal are COPIED (a hard link would let a later cp -f change the original) and every stage from the cut on runs again into the new dir.
# REFREEZE MODE (lane-snap6; the operator via science 6 Nov 02:50Z): see apply-refreeze notes in lane-snap6/NOTES.md. REFREEZE_FROM=<the 09:00Z seal>, t = the re-freeze instant.
REFREEZE_FROM=${REFREEZE_FROM:-}; REFREEZE_SET=${REFREEZE_SET:-}
if [ -n "$REFREEZE_FROM" ]; then
  [ -z "${RESUME_FROM:-}" ] || { echo "snapshot-interim: REFREEZE_FROM and RESUME_FROM exclude each other" >&2; exit 66; }
  [ -d "$REFREEZE_FROM/frozen/main" ] && [ -s "$REFREEZE_FROM/frozen/main/state.sqlite" ] || { echo "snapshot-interim: REFREEZE_FROM $REFREEZE_FROM has no frozen/main store" >&2; exit 66; }
  [ "$REFREEZE_FROM" != "$SEAL" ] || { echo "snapshot-interim: the rerun must be a NEW sealed directory" >&2; exit 66; }
  cp -a "$REFREEZE_FROM/frozen/." "$SEAL/frozen/" || { echo "snapshot-interim: could not copy the earlier seal's frozen/" >&2; exit 66; }
  [ -n "$REFREEZE_SET" ] || REFREEZE_SET=$(python3 -I "$V/launch/late-set.py" --from-seal "$REFREEZE_FROM" 2>/dev/null)
  export REFREEZE_FROM REFREEZE_SET; export CODERS_LATE=${CODERS_LATE:-1}; [ "$CODERS_LATE" != 1 ] || export CODERS_TREE=${CODERS_TREE:-$V/inspection-coders/tree-ffe1cf34}
  [ "$FINAL" != true ] || FINAL_T_ISO=${FINAL_T_ISO:-$T}
  echo "refreeze: from $REFREEZE_FROM, stores to fetch again: ${REFREEZE_SET:-none}; final-t ${FINAL_T_ISO:-n/a}" >&2
  [ -n "$REFREEZE_SET" ] || { echo "snapshot-interim: no store holds a late run in flight: nothing to re-freeze (the 09:00Z seal stands)" >&2; exit 67; }
fi
# RESTART MODE (lane-snap6): see launch/final-restart.sh. RESTART_FROM=<the stopped seal of the SAME t, renamed aside>; the new seal keeps the original name.
RESTART_FROM=${RESTART_FROM:-}
if [ -n "$RESTART_FROM" ]; then
  [ -z "${RESUME_FROM:-}${REFREEZE_FROM:-}" ] || { echo "snapshot-interim: RESTART_FROM excludes RESUME_FROM and REFREEZE_FROM" >&2; exit 66; }
  [ -d "$RESTART_FROM/M" ] && [ -s "$RESTART_FROM/frozen/main/state.sqlite" ] || { echo "snapshot-interim: RESTART_FROM $RESTART_FROM lacks M/ or frozen/main" >&2; exit 66; }
  [ "$RESTART_FROM" != "$SEAL" ] || { echo "snapshot-interim: RESTART_FROM must be the stopped seal renamed aside, not the new seal" >&2; exit 66; }
  cp -a "$RESTART_FROM/frozen/." "$SEAL/frozen/" && cp -a "$RESTART_FROM/M" "$SEAL/M" || { echo "snapshot-interim: could not copy the stopped seal's frozen/ or M/" >&2; exit 66; }
  rm -f "$SEAL"/frozen/correction-capped-*.json "$SEAL"/frozen/correction-unscorable-*.json; [ ! -f "$SEAL/frozen/input-shas.txt" ] || { grep -v -E 'correction-(capped|unscorable)-' "$SEAL/frozen/input-shas.txt" > "$SEAL/frozen/input-shas.txt.new"; mv -f "$SEAL/frozen/input-shas.txt.new" "$SEAL/frozen/input-shas.txt"; }      # the stopped seal's correction copies are replaced by this run's (a stale 7-row file must not sit in the final's frozen/)
  [ ! -f "$RESTART_FROM/logs/h3_catchup.out" ] || ln -s "$RESTART_FROM/logs/h3_catchup.out" "$SEAL/logs/h3_catchup.out"
  [ -z "${H3_CATCHUP_PID:-}" ] || export H3_CATCHUP_PID H3_CATCHUP_DEADLINE=${H3_CATCHUP_DEADLINE:-$(( TS + 11700 ))}
  echo "restart: from $RESTART_FROM (frozen/ and M/ reused; bmerge.json is regenerated by the driver); H3 catch-up pid ${H3_CATCHUP_PID:-none}" >&2
fi
RESUME_FROM=${RESUME_FROM:-}
if [ -n "$RESUME_FROM" ]; then
  [ -d "$RESUME_FROM/M" ] && [ -d "$RESUME_FROM/frozen" ] && [ -d "$RESUME_FROM/inspection" ] || { echo "snapshot-interim: RESUME_FROM $RESUME_FROM lacks M/, frozen/ or inspection/" >&2; exit 66; }
  [ "$(basename "$RESUME_FROM" | sed 's/-r[0-9]*$//')" = "$(basename "$SEAL" | sed -E 's/-(r[0-9]*|sens)$//')" ] || { echo "snapshot-interim: RESUME_FROM must be a seal of the same t and prefix" >&2; exit 66; }
  cp -a "$RESUME_FROM/frozen/." "$SEAL/frozen/" && cp -a "$RESUME_FROM/M" "$SEAL/M" && cp -a "$RESUME_FROM/inspection" "$SEAL/inspection" && { [ ! -d "$RESUME_FROM/coder_replay" ] || cp -a "$RESUME_FROM/coder_replay" "$SEAL/coder_replay"; } || { echo "snapshot-interim: could not copy the reused seal" >&2; exit 66; }
fi
P0=$(date +%s)
now() { date -u +%FT%TZ; }
say() { echo "$(now) $*"; }
# stage NAME CMD...: runs CMD with stdout/stderr into logs/NAME.{out,err}, times it, appends one JSON line; returns CMD's rc
stage() {
  local name=$1; shift
  local s0 s1 rc
  if [ "${SKIP_MAIN:-0}" = 1 ] && [ -n "${RESUME_FROM:-}" ]; then
    case $name in analyse|cut_kaug|analyse_kaug|cut_coded|prewarm_coded|analyse_coded|cut_coded_kaug|analyse_coded_kaug|cell_counts|run_level|h3|layout|second_kappa|exhibits|records_primary|records_all|primary_json|fidelity_extra|bytes_contrast|extent_account|structure) say "stage $name: skipped (SKIP_MAIN: the sensitivities only)"; return 0;; esac
  fi
  if [ -n "${RESTART_FROM:-}" ]; then
    case $name in final_pulls|freeze_*|merge|fidelity_pull|quiesce|coders_merge|freeze_site_ba|hpc_tar_ages) say "stage $name: reused from the stopped seal $RESTART_FROM (not run)"; return 0;; esac
  fi
  if [ -n "${REFREEZE_FROM:-}" ]; then
    case $name in final_pulls|freeze_main|fidelity_pull|quiesce|coders_merge|freeze_site_ba) say "stage $name: reused/skipped in the re-freeze rerun (the 09:00Z seal's copy stands)"; return 0;; esac
  fi
  if [ -n "${RESUME_FROM:-}" ]; then
    case $name in final_pulls|freeze_*|merge|fidelity_pull|quiesce|coders_merge|coder_replay_start|coder_replay_collect) say "stage $name: reused from $RESUME_FROM (not run)"; return 0;; esac
  fi
  s0=$(date +%s.%N)
  "$@" > "$SEAL/logs/$name.out" 2> "$SEAL/logs/$name.err" < /dev/null; rc=$?
  s1=$(date +%s.%N)
  python3 -I -c 'import json,sys; n,a,b,rc=sys.argv[1:5]; print(json.dumps({"stage":n,"start":float(a),"end":float(b),"seconds":round(float(b)-float(a),1),"rc":int(rc)}))' \
    "$name" "$s0" "$s1" "$rc" >> "$STAGES"
  say "stage $name rc=$rc seconds=$(python3 -I -c "print(round($s1-$s0,1))")"
  printf '%s %s rc=%s seconds=%s\n' "$(now)" "$name" "$rc" "$(python3 -I -c "print(round($s1-$s0,1))")" >> "$SEAL/stage-markers.txt"      # the delivery marker: this stage's output is in the seal from this time
  return $rc
}
note() { python3 -I -c 'import json,sys; print(json.dumps({"note":sys.argv[1],"value":json.loads(sys.argv[2])}))' "$1" "$2" >> "$STAGES"; }
emit() {
  local rc=$1
  python3 -I - "$STAGES" "$SEAL/timings.json" "$T" "$P0" "$rc" <<'EOF'
import json, sys, time
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
st = [r for r in rows if "stage" in r]
out = {"t": sys.argv[3], "driver_start_unix": int(sys.argv[4]), "total_s": round(time.time() - int(sys.argv[4]), 1), "exit": int(sys.argv[5]),
       "stages": st, "notes": {r["note"]: r["value"] for r in rows if "note" in r}}
json.dump(out, open(sys.argv[2], "w"), indent=1)
print("timings: " + " ".join(f"{r['stage']}={r['seconds']}s(rc{r['rc']})" for r in st) + f" total={out['total_s']}s under_1h={out['total_s'] < 3600}")
EOF
  chmod 600 "$SEAL/timings.json" 2>/dev/null
  # the lead's report set (amendment 43): sealed path, stage timings, whole-run counts; also in $SEAL/report.txt
  python3 -I "$V/launch/snapshot_report.py" "$SEAL" 2>&1 | sed 's/^/report: /'
}
finish() { emit "$1"; exit "$1"; }

say "interim snapshot t=$T cut=$(date -u -d "@$((TS - CAP_S))" +%FT%TZ) cap_s=$CAP_S no_outcome=$NO_OUTCOME final=$FINAL out=$SEAL"

# page-cache warm-up (the disk is latency-bound: pcache's serial fingerprint reads 130 files/s cold, 1500/s with 64 readers; measured 5 Nov): while the freeze waits, the done run dirs of the live merged store that
# started before the cut are read by many readers at once, so the fingerprint finds them cached (prewarm.py changes nothing on disk)
if [ "${PREWARM:-1}" = 1 ] && [ -f "$V/coding-merged/current/state.sqlite" ]; then
  python3 -I "$V/launch/prewarm.py" --state "$V/coding-merged/current/state.sqlite" --before "$(date -u -d "@$((TS - CAP_S))" +%FT%TZ)" --threads "${PREWARM_EARLY_THREADS:-32}" > "$SEAL/logs/prewarm_early.out" 2>&1 < /dev/null &
fi

# ---- 1. freeze: main's mirror loop fetched once after t, every B store fetched after t; the stores copied (state.sqlite and fetch.json only) into frozen/ ----------------
# the store is copied at the START of a fetch and fetch.json is written at its END (after the rsyncs): the copy's own time is fetched_utc minus seconds.
# A fetch that failed on a directory writes fetch.json with store_replaced=false and leaves the OLD state.sqlite: that is no copy at t, so it prints nothing (the assert).
copied_at() { python3 -I -c "import json,datetime as dt,sys; j=json.load(open(sys.argv[1]+'/fetch.json')); assert j.get('store_replaced') is True and not j.get('failed'); print(int(dt.datetime.fromisoformat(j['fetched_utc'].replace('Z','+00:00')).timestamp()-j['seconds']))" "$1" 2>/dev/null; }
freeze_main() {
  local deadline=$(( $(date +%s) + FREEZE_WAIT_S )) c
  while :; do
    c=$(copied_at "$MAIN_MIRROR")
    [ -n "$c" ] && [ "$c" -ge "$TS" ] && { echo "main store copied at t+$(( c - TS ))s"; return 0; }
    [ "$(date +%s)" -lt "$deadline" ] || { echo "main mirror: no store copy after t within ${FREEZE_WAIT_S}s (last copy at t${c:+$(printf '%+d' $(( c - TS )))}s)"; return 1; }
    sleep 15
  done
}
freeze_b() {          # an at-once fetch of every B store (the loop's flock keeps it from racing the loop), then the same freshness check
  local p c rc=0
  PAR=1 bash "$V/launch/b-mirrors.sh" once ${REFREEZE_SET:-$PROVIDERS} || { echo "at least one B fetch failed (the previous mirror of that store stands, and is not fresh)"; rc=1; }
  for p in ${REFREEZE_SET:-$PROVIDERS}; do
    c=$(copied_at "$SNAP_B/$p")
    echo "$p store copied at t${c:+$(printf '%+d' $(( c - TS )))}s"
    [ -n "$c" ] && [ "$c" -ge "$TS" ] || rc=1
  done
  return $rc
}
# the fixed snapshot's own last fetch of main's mirror and last pull of site_g's audit log, right after t (bounded; a failure is a flag, not a stop)
if [ "$FINAL_MODE" = true ] && [ "${FINAL_PULLS:-1}" = 1 ]; then
  stage final_pulls bash "$V/launch/final-pulls.sh" || say "WARNING (FLAG): the final's own mirror fetch or audit pull did not report ok: logs/final_pulls.out"
  sed 's/^/  /' "$SEAL/logs/final_pulls.out" 2>/dev/null | cut -c1-200
fi
stage freeze_main freeze_main; FM=$?
say "coders' merged store: the last generation before the final's merge is $(basename "$(readlink -f "$V/coding-merged/current")")"
stage freeze_b freeze_b; FB=$?
[ "$FINAL_MODE" != true ] || { stage coders_merge bash "$V/launch/b-mirrors.sh" merge || true; say "coders' merged store after the final's merge: $(basename "$(readlink -f "$V/coding-merged/current")") (loop3.sh is not touched by the quiesce)"; }      # the coders read coding-merged/current, which only the mirror loop (or this call) publishes
# a dispatcher with a launch file (b/launch/icsa-*.json, b/launch-site_a/icsa-*.json) that is in no mirror is in no merge, no coding and no snapshot (icsa-site_a-1, 5 Nov 11:2xZ): say it loudly, note it in
# timings.json and the report. A launch file alone may be a plan not yet started (site_s, 5 Nov), so it is a flag, not a stop; a started one with no mirror is for the lead to read from this line.
UNMIRRORED=$(python3 -I - "$V" $PROVIDERS <<'PYU'
import glob, os, sys
V, have = sys.argv[1], set(sys.argv[2:])
exp = sorted({os.path.basename(f)[:-5] for d in ("b/launch", "b/launch-site_a") for f in glob.glob(f"{V}/{d}/icsa-*.json") if not f.endswith(".block.json")})
print(" ".join(e for e in exp if e not in have or not os.path.isfile(f"{V}/snap-b/{e}/state.sqlite")))
PYU
)
# the memory-retry ledger (a run that failed on memory gets one retry at a larger limit; operator, 5 Nov): kept in the seal per run (provider, run key, cap, outcome); the terminal gets counts
if [ -s "$V/lane-snap4/memretry/ledger.jsonl" ]; then
  cp -f "$V/lane-snap4/memretry/ledger.jsonl" "$SEAL/frozen/memretry.jsonl" && chmod 600 "$SEAL/frozen/memretry.jsonl"
  say "memory retries (cap 32 GiB, one per run): $(python3 -I -c 'import json,sys; r=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]; print("runs=%d ok=%d still_failed=%d" % (len(r), sum(x["outcome"]=="ok" for x in r), sum(x["outcome"]!="ok" for x in r)))' "$SEAL/frozen/memretry.jsonl")"
fi
if [ -n "$UNMIRRORED" ]; then
  say "WARNING (FLAG): launch file(s) with NO mirror in this snapshot: $UNMIRRORED (a started dispatcher among them has runs in no snapshot)"
  note unmirrored_dispatchers "$(python3 -I -c 'import json,sys; print(json.dumps(sys.argv[1].split()))' "$UNMIRRORED")"
fi
# the coders' counts (lane-code76's coded_counts.py: from their plan and the existence of their pair/final files, never an answer), at the freeze, into the sealed dir; if their tool cannot run,
# the file it last wrote is copied. cell_counts.py joins it on to the main block's rows.
CODERS_PY=${CODERS_PY:-$V/inspection-coders/tree-52ddcad8/.venv/bin/python}; CODERS_TOOL=${CODERS_TOOL:-$V/inspection-coders/coded_counts.py}
stage freeze_coders_counts bash -c "$CODERS_PY $CODERS_TOOL --out $SEAL/frozen/coders_counts.csv || cp -f $V/inspection-coders/coded_counts.csv $SEAL/frozen/coders_counts.csv" || say "WARNING: no coders' counts at the freeze (cell_counts.csv will leave coders_* empty)"
# the per-day truth of lane-h3b's relabel loop (.16), copied into the seal with the age of its last completed pass; H3's measure reads it for the stricter readings (a stale or missing copy is reported, not hidden)
stage freeze_daytruth bash "$V/launch/daytruth_pull.sh" "$SEAL" "$T" || say "WARNING: no per-day truth copied (the measure's stricter readings stay no_day_truth): logs/freeze_daytruth.out"
sed 's/^/  /' "$SEAL/logs/freeze_daytruth.out" 2>/dev/null | cut -c1-220
# the run hosts' kernel hung-task lines (lane-layout's contract, science 5 Nov 05:06Z): frozen/kernel-hung/<store>__<host>.log (+ .since); an unreadable host leaves NO file (unknown), an empty file is zero
stage freeze_kernelhung bash "$V/launch/kernel_hung_pull.sh" "$SEAL" || say "WARNING: a run host's kernel journal could not be read (its file is absent = unknown to the reader): logs/freeze_kernelhung.out"
# the site_ba slots (lane-layout's backend_shares.csv splits site_ba from site_a by slot name; science 5 Nov 05:59Z): the slot names of the run VM's extra-slots.json, frozen as frozen/site_ba-slots.txt
stage freeze_site_ba bash "$V/launch/site_ba_slots_pull.sh" "$SEAL" || say "WARNING: the run VM's extra slots could not be read (no site_ba-slots.txt: the layout reader's default, gemma-107, stands)"
if [ -z "${RESUME_FROM:-}" ] && [ -z "${REFREEZE_FROM:-}" ] && [ -z "${RESTART_FROM:-}" ]; then stage hpc_tar_ages bash "$V/launch/hpc_tar_ages.sh" "$SEAL" "$TS" || say "WARNING: the HPC store tars' ages could not be recorded (see logs/hpc_tar_ages.out)"; sed 's/^/  /' "$SEAL/logs/hpc_tar_ages.out" 2>/dev/null | cut -c1-200; fi
# the exclusion list in force (leases a foreign actor shared a slot user with: marked not_observed:foreign_lines), kept in the seal as it stood
cp -f "$V/lane-snap4/h3-exclusions.tsv" "$SEAL/frozen/h3-exclusions.tsv" 2>/dev/null || true
if [ -f "$V/b/checkpoint-6c/flag-lab504-14.json" ] && [ "$(sha256sum "$V/b/checkpoint-6c/flag-lab504-14.json" | cut -d" " -f1)" = 4d5a505fa81b4aed0f3e34d2fec78b1fda06f8b41038f571e4c58d14d43fd728 ]; then cp -f "$V/b/checkpoint-6c/flag-lab504-14.json" "$SEAL/frozen/flag-lab504-14.json" && chmod 600 "$SEAL/frozen/flag-lab504-14.json"; fi      # the Lab-504 sensitivity's runs
# the HPC trace budget table (lane-hpcsbx; science 5 Nov 23:37Z): copied as is, never read here; a missing file is a note
if [ -f "$V/lane-snap4/hpc-trace-budget.csv" ]; then cp -f "$V/lane-snap4/hpc-trace-budget.csv" "$SEAL/frozen/hpc-trace-budget.csv" && chmod 600 "$SEAL/frozen/hpc-trace-budget.csv" && say "hpc-trace-budget.csv copied into frozen/ (not read)"; else say "note: lane-snap4/hpc-trace-budget.csv does not exist (not copied)"; fi
# main's extract inputs (the restart log, site_g's monitor log, the run hosts' quarantines): read-only copies from .23 and a check on .8, once per interim, at the freeze (the lead, 4 Nov)
stage freeze_inputs bash "$V/launch/h3-loop.sh" inputs; FI=$?
# the final: the loops that only feed later snapshots are stopped now (their running children finish), so the host's cores are the analysis's; the extract loop keeps going for the H3 catch-up
if [ "$FINAL_MODE" = true ] && [ "${QUIESCE:-1}" = 1 ]; then stage quiesce bash "$V/launch/quiesce-loops.sh" || true; fi
if [ "$FINAL_MODE" = true ] && [ "${LATE_LOOP:-1}" = 1 ] && [ -z "$RESUME_FROM" ] && [ -z "${RESTART_FROM:-}" ]; then setsid nohup bash "$V/launch/late-mirror-loop.sh" run > /dev/null 2>&1 < /dev/null & say "late-store mirror loop started (light, every 3 min, until 10:20Z): lane-snap6/late-mirror/loop.log"; fi
# the fixed snapshot's H3 catch-up (science: a run no pass reached reads not_observed:no_final_pass): one pass of every audit store now, in the background, while the analysis runs; the H3 stage waits for it
if [ "$FINAL_MODE" = true ] && [ "${H3_CATCHUP:-1}" = 1 ] && [ -z "$RESUME_FROM" ] && [ -z "${RESTART_FROM:-}" ]; then
  bash "$V/launch/h3-catchup.sh" > "$SEAL/logs/h3_catchup.out" 2>&1 < /dev/null & export H3_CATCHUP_PID=$!
  export H3_CATCHUP_DEADLINE=${H3_CATCHUP_DEADLINE:-$(( TS + 11700 ))}       # t + 105 min: site_g's pass is the long one (about 45 min once the host is quiet)
  say "h3 catch-up started in the background (pid $H3_CATCHUP_PID, waited for until t+105min)"
fi
[ $FI -eq 0 ] || say "WARNING: main's extract inputs are not fresh (h3-loop.sh inputs rc=$FI): main's extract will not run on stale inputs; the status will be 6"
python3 -I - "$SEAL" "$MAIN_MIRROR" "$SNAP_B" "$TS" $PROVIDERS <<'EOF'
import hashlib, json, shutil, sys, os, time, datetime as dt
seal, main, snapb, ts = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
names = ["main"] + sys.argv[5:]
roots = {"main": main, **{p: os.path.join(snapb, p) for p in sys.argv[5:]}}
def utc(x): return dt.datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp()
def copy_pair(src, dst):
    """state.sqlite and fetch.json of ONE fetch generation: fetch replaces state.sqlite by rename and writes fetch.json after it, so read fetch.json, copy the store, and accept the
    pair only if fetch.json is unchanged, the store's (size, mtime) did not move, and the store is not newer than the fetch.json that describes it (+2 s)."""
    for _ in range(6):
        f1 = open(os.path.join(src, "fetch.json"), "rb").read()
        st1 = os.stat(os.path.join(src, "state.sqlite"))
        shutil.copyfile(os.path.join(src, "state.sqlite"), os.path.join(dst, "state.sqlite"))
        st2 = os.stat(os.path.join(src, "state.sqlite"))
        f2 = open(os.path.join(src, "fetch.json"), "rb").read()
        if f1 == f2 and (st1.st_size, st1.st_mtime_ns) == (st2.st_size, st2.st_mtime_ns) and st1.st_mtime <= utc(json.loads(f1)["fetched_utc"]) + 2:
            import sqlite3
            c = sqlite3.connect(os.path.join(dst, "state.sqlite"))
            try:
                n = c.execute("SELECT count(*) FROM runs").fetchone()[0]
            finally:
                c.close()
            if n == json.loads(f1)["runs"]:          # the store holds the run count its fetch.json states (a second, independent check of the generation)
                open(os.path.join(dst, "fetch.json"), "wb").write(f1)
                return
        time.sleep(5)
    raise SystemExit(f"{src}: the store and its fetch.json kept changing for 30 s: no consistent pair")
lag = {}
for n in names:
    d = os.path.join(seal, "frozen", n)
    reuse = bool(os.environ.get("RESUME_FROM")) or (bool(os.environ.get("REFREEZE_FROM")) and n not in os.environ.get("REFREEZE_SET", "").split())
    if not reuse:            # a rerun reuses the earlier seal's frozen stores (copied); a re-freeze copies only its set again
        os.makedirs(d, mode=0o700, exist_ok=True)      # a re-freeze: the copied frozen/<store>/ exists already
        copy_pair(roots[n], d)
    fj = json.load(open(os.path.join(d, "fetch.json")))
    t = utc(fj["fetched_utc"]) - fj["seconds"]
    lag[n] = {"store_copied_after_t_s": int(t - ts), "finished_dirs": fj["finished_dirs"], "runs": fj["runs"], "store_replaced": fj.get("store_replaced"),
              "store_sha256": hashlib.sha256(open(os.path.join(d, "state.sqlite"), "rb").read()).hexdigest()[:16]}
print(json.dumps(lag, sort_keys=True))
EOF
rc=$?; [ $rc -eq 0 ] || { say "freeze: could not copy a store (rc=$rc)"; finish 3; }
note mirrors_freshness "$(python3 -I -c "
import json,os,datetime as dt
seal='$SEAL'; ts=$TS; out={}
for n in sorted(x for x in os.listdir(seal+'/frozen') if os.path.isfile(seal+'/frozen/'+x+'/fetch.json')):          # the stores only: frozen/ also holds the coders' counts and labels files and the daytruth / kernel-hung directories (no fetch.json)
    fj=json.load(open(f'{seal}/frozen/{n}/fetch.json')); t=dt.datetime.fromisoformat(fj['fetched_utc'].replace('Z','+00:00')).timestamp()-fj['seconds']
    out[n]={'store_copied_after_t_s':int(t-ts),'finished_dirs':fj['finished_dirs'],'runs':fj['runs']}
print(json.dumps(out,sort_keys=True))")"
[ $FM -eq 0 ] || say "WARNING: main's mirror is older than t (a snapshot of a store before t misses what finished in between): see freshness"
[ $FB -eq 0 ] || say "WARNING: at least one B mirror is older than t: see freshness"
note freeze_ok "{\"main\": $([ $FM -eq 0 ] && echo true || echo false), \"b\": $([ $FB -eq 0 ] && echo true || echo false)}"

# ---- 2. merge ------------------------------------------------------------------------------------------------------------------------------------------------------------
BARGS=(); for p in $PROVIDERS; do BARGS+=(--b "$p=$SEAL/frozen/$p"); done
cd "$TREE" || finish 3
export ICSA_DATA=$V PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# a heavy stage starts only when MemAvailable allows it (this host hangs instead of OOM-killing): wait up to GATE_WAIT_S, then refuse (rc 75), never go on regardless
MIN_AVAIL_GIB=${MIN_AVAIL_GIB:-$(( MEMCAP + 4 ))}; GATE_WAIT_S=${GATE_WAIT_S:-900}
memgate() {
  local deadline=$(( $(date +%s) + GATE_WAIT_S )) a
  while :; do
    a=$(awk '/MemAvailable/{printf "%d", $2/1048576}' /proc/meminfo)
    [ "$a" -ge "$MIN_AVAIL_GIB" ] && return 0
    [ "$(date +%s)" -lt "$deadline" ] || { echo "memgate: MemAvailable ${a}GiB < ${MIN_AVAIL_GIB}GiB for ${GATE_WAIT_S}s: refused"; return 75; }
    sleep 20
  done
}
RUN() { memgate || return 75; nice -n 10 "$V/bin/memcap" "$MEMCAP" "$PY" "$@"; }
# interim knob (lane-snap6, the lead 5 Nov): main's runs with NO pipeline-cache entry at the freeze (at most SNAP_SKIP_MAIN_MAX, default 6) are counted failed (reason labelling_not_finished) by the
# analysis instead of being computed inline for ~50 min or hours; a hit is served as always; MORE than the maximum: the knob stands down and everything computes inline (said in the log). Off in
# FINAL_MODE (the operator: the final waits) and when INTERIM_SKIP=0. snap_wrap.py stands in front of postrun.process_run only; pcache.py and the frozen tree are untouched.
SNAPCLI=(-m snapshot)
unset SNAP_SKIP_LIST
if [ "$FINAL_MODE" != true ] && [ "${INTERIM_SKIP:-0}" = 1 ]; then      # OFF by default since 5 Nov 18:28Z: the frozen analysis refuses a cut whose done run has no scored row (the 18:00Z analysis failed on it)
  export SNAP_SKIP_MAIN_MAX=${SNAP_SKIP_MAIN_MAX:-6}; SNAPCLI=("$V/launch/snap_wrap.py")
  say "interim knob ON: main's runs with no pipeline-cache entry at the freeze (at most $SNAP_SKIP_MAIN_MAX) are counted failed (labelling_not_finished), not computed inline; more than that: stands down"
else
  unset SNAP_SKIP_MAIN_MAX
fi
skip_note() { python3 -I -c 'import json,sys; m=json.load(open(sys.argv[1])); print("%s: %d run(s) counted failed as labelling_not_finished (all failed=%d)" % (sys.argv[2], m["counts"].get("failed_by_reason",{}).get("labelling_not_finished",0), m["counts"].get("failed",0)))' "$1" "$2" 2>/dev/null || echo "$2: manifest not readable"; }
stage merge RUN -m snapshot.bmerge stores --main-root "$SEAL/frozen/main" "${BARGS[@]}" --out "$SEAL/M"; rc=$?
say "merge: $(tail -n 1 "$SEAL/logs/merge.out" 2>/dev/null)"
[ $rc -eq 0 ] || { say "merge FAILED: $(tail -n 2 "$SEAL/logs/merge.err" | cut -c1-300)"; finish 4; }

# ---- 3. config for assemble: main = site_g, each provider its own cache, index and data dir ---------------------------------------------------------------------------------
python3 -I - "$SEAL" "$CACHE_MAIN" "$CACHE_B" "$IDX_B" "$V/s1z" $PROVIDERS > "$SEAL/bmerge.json" <<'EOF'
import json, sys
seal, cm, cb, ib, dd, *prov = sys.argv[1:]
print(json.dumps({"merge_root": f"{seal}/M", "providers": {"site_g": {"cache": cm}, **{p: {"cache": f"{cb}/{p}", "index_root": f"{ib}/{p}", "data_dir": dd} for p in prov}}}, indent=1))
EOF
for p in $PROVIDERS; do [ -d "$CACHE_B/$p" ] || { mkdir -p -m 700 "$CACHE_B/$p"; }; done        # an empty cache for a provider that has none yet: its runs would all be planned misses

# ---- 4. cut ----------------------------------------------------------------------------------------------------------------------------------------------------------------
# the coders' labels (#76) and their coverage, when given: copied at the freeze into the sealed dir (a copy is read, never the file the coders are writing) and passed to the snapshot
# fault calibration's adapter rows and h3 table (calibrate score --partial on a COPY of its root on .23): unless H3_TABLE/FIDELITY_ROWS were given, they are made here
if [ -z "$H3_TABLE" ] && [ "$FIDELITY_ROWS" = none ] && [ "${FIDELITY_SCORE:-1}" = 1 ]; then
  stage fidelity_pull bash "$V/launch/fidelity_score.sh" pull "$SEAL"; FSC=$?
  sed 's/^/  /' "$SEAL/logs/fidelity_pull.out" 2>/dev/null | cut -c1-200
  if [ $FSC -eq 0 ]; then H3_TABLE=$SEAL/frozen/fault/h3_table.csv; FIDELITY_ROWS=$SEAL/frozen/fault/adapter_rows.jsonl
  else say "WARNING: fault calibration could not be scored (logs/fidelity_pull.out): the fidelity exhibit says tested=False"; fi
fi
H3T=(); [ -z "$H3_TABLE" ] || H3T=(--h3-table "$H3_TABLE")
INS=(); if [ "$INSPECTION" != none ]; then
  cp -f "$INSPECTION" "$SEAL/frozen/inspection-labels.jsonl" && INSPECTION=$SEAL/frozen/inspection-labels.jsonl || { say "inspection labels $INSPECTION could not be copied"; finish 3; }
  if [ -n "${INSPECTION_COVERAGE:-}" ]; then cp -f "$INSPECTION_COVERAGE" "$SEAL/frozen/inspection-coverage.jsonl" && INS=(--inspection-coverage "$SEAL/frozen/inspection-coverage.jsonl") || { say "inspection coverage could not be copied"; finish 3; }; fi
fi
[ -n "${COHORT_CUT:-}" ] || { [ "$FINAL_MODE" = true ] && [ -s "$V/lane-snap6/cohort-cut.txt" ] && COHORT_CUT=$(head -n 1 "$V/lane-snap6/cohort-cut.txt" | tr -d " \r"); }      # the scheduler's environment cannot change: the instant is read from this file, written at ~08:55Z
case "${COHORT_CUT:-}" in ""|????-??-??T??:??:??Z|????-??-??T??:??:??.*Z) ;; *) say "cohort cut file/env is not an ISO UTC instant (${COHORT_CUT}): ignored"; COHORT_CUT=;; esac
CC=(); [ -z "${COHORT_CUT:-}" ] || { CC=(--cohort-cut "$COHORT_CUT"); say "cohort cut: $COHORT_CUT (instead of t - cap), applied by recohort; the table at the default cut goes to out-050/"; }
[ -z "${FINAL_T_ISO:-}" ] || { CC+=(--final-t "$FINAL_T_ISO"); say "final-t: --final true is tied to $FINAL_T_ISO (the rerun after the re-freeze), not to 09:00Z"; }
# the final's switches come from a FILE (the scheduler's environment cannot be changed): lane-snap6/final-flags.env, lines like CAPPED_CORR=1 / KAUG=1 / KAUG_PRIMARY=1; absent = every switch at its default
FFILE=${FINAL_FLAGS_FILE:-$V/lane-snap6/final-flags.env}
if [ "$FINAL_MODE" = true ]; then
  if [ -f "$FFILE" ]; then . "$FFILE"; else say "WARNING (FLAG): $FFILE is absent: the 09:00Z plan's defaults are used (CAPPED_CORR=1 KAUG=1 OVERHEAD_FINAL=1, sensitivities off)"; fi
  : "${CAPPED_CORR:=1}" "${KAUG:=1}" "${OVERHEAD_FINAL:=1}" "${CAPPED_SENS:=0}" "${LAB504_SENS:=0}" "${SENS_050:=0}"      # a missing switch means the registered plan of the final, never a silent off for the correction
fi
say "final switches: CAPPED_CORR=${CAPPED_CORR:-0} KAUG=${KAUG:-0} OVERHEAD_FINAL=${OVERHEAD_FINAL:-0} CAPPED_SENS=${CAPPED_SENS:-1} LAB504_SENS=${LAB504_SENS:-1} SENS_050=${SENS_050:-1} (file $FFILE: $([ -f "$FFILE" ] && echo present || echo absent))"
CAPPED_ON=
COMMON2=()
# the final's overhead input (the overhead window's result2: 30 records, 3 rows, 0 cells below k): used when OVERHEAD_FINAL=1 in final-flags.env and nothing else names an overhead file
if [ "${OVERHEAD_FINAL:-0}" = 1 ] && [ "$OVERHEAD" = none ] && [ -s "$V/scripted/overhead-window/result2/enforcement_overhead.json" ]; then OVERHEAD=$V/scripted/overhead-window/result2/enforcement_overhead.json; say "overhead input: $OVERHEAD (sha256 $(sha256sum "$OVERHEAD" | cut -c1-16))"; cp -f "$OVERHEAD" "$SEAL/frozen/enforcement_overhead.json" 2>/dev/null; fi
# the correction file's name and sha come from lane-snap6/capped-input.env (CAPPED_NAME=, WANT_CAPPED_SHA=; science's 8-row file, 6 Nov 09:2xZ); the older 7-row pair is the default only when that file is absent
if [ "$FINAL_MODE" = true ] && [ "${CAPPED_CORR:-0}" = 1 ] && [ ! -f "$V/lane-snap6/capped-input.env" ]; then say "REFUSED (fail-closed, exit 70): lane-snap6/capped-input.env (the correction file's name and sha256) does not exist: the final does not run without it"; exit 70; fi
[ ! -f "$V/lane-snap6/capped-input.env" ] || . "$V/lane-snap6/capped-input.env"
: "${CAPPED_NAME:=correction-capped-7.json}" "${WANT_CAPPED_SHA:=89acd256c278e9bf24aa34bc28906b35084fd30e99991e3611f14d7fcd4b495a}"
WANT_LAB504_SHA=4d5a505fa81b4aed0f3e34d2fec78b1fda06f8b41038f571e4c58d14d43fd728
if [ "${CAPPED_CORR:-0}" = 1 ] && [ "$(sha256sum "$V/b/checkpoint-6c/${CAPPED_NAME}" 2>/dev/null | cut -d" " -f1)" != "$WANT_CAPPED_SHA" ]; then say "WARNING (FLAG): ${CAPPED_NAME} is not the expected file (sha256 != $WANT_CAPPED_SHA): the capped correction is NOT applied"; [ "$FINAL_MODE" != true ] || { say "REFUSED (fail-closed, exit 70): the final does not run without the registered correction file: fix lane-snap6/capped-input.env or the file and start again"; exit 70; }; CAPPED_CORR=0; fi
if [ "${CAPPED_CORR:-0}" = 1 ] && [ -s "$V/b/checkpoint-6c/${CAPPED_NAME}" ]; then
  cp -f "$V/b/checkpoint-6c/${CAPPED_NAME}" "$SEAL/frozen/${CAPPED_NAME}" && chmod 600 "$SEAL/frozen/${CAPPED_NAME}" && CAPPED_ON=1 && CC+=(--capped-correction "$SEAL/frozen/${CAPPED_NAME}" --capped-stores "$SEAL/frozen")
  if [ "${CAPPED_I48:-0}" = 1 ]; then      # science 6 Nov 09:25Z: I48 D S1 (done by the time cap, unscorable here: memory) counts K BY COUNT, no measures, through the capped path: a SEPARATE small file, sha-checked, fail-closed
    UF=$V/lane-snap6/correction-unscorable-1.json
    if [ "$(sha256sum "$UF" 2>/dev/null | cut -d" " -f1)" != "$(cut -d" " -f1 "$V/lane-snap6/correction-unscorable-1.sha256" 2>/dev/null)" ] || [ -z "$(cut -d" " -f1 "$V/lane-snap6/correction-unscorable-1.sha256" 2>/dev/null)" ]; then say "REFUSED (fail-closed, exit 70): CAPPED_I48=1 but lane-snap6/correction-unscorable-1.json is missing or does not match its .sha256"; exit 70; fi
    cp -f "$UF" "$SEAL/frozen/correction-unscorable-1.json" && chmod 600 "$SEAL/frozen/correction-unscorable-1.json" && CC+=(--unscorable-correction "$SEAL/frozen/correction-unscorable-1.json") && { sha256sum "$SEAL/frozen/correction-unscorable-1.json" | sed "s|$SEAL/frozen/||" >> "$SEAL/frozen/input-shas.txt"; say "CAPPED_I48=1: main I48 D S1 counts K BY COUNT, no measures (time-capped, unscorable here: memory): correction-unscorable-1.json sha256 $(sha256sum "$UF" | cut -c1-16)"; }
  fi
  { sha256sum "$SEAL/frozen/${CAPPED_NAME}"; [ ! -s "$SEAL/frozen/flag-lab504-14.json" ] || sha256sum "$SEAL/frozen/flag-lab504-14.json"; } | sed "s|$SEAL/frozen/||" >> "$SEAL/frozen/input-shas.txt"
  say "capped correction ON (option B): $(sha256sum "$SEAL/frozen/${CAPPED_NAME}" | cut -c1-16)...; only where the capped attempt is the run's earliest analysable attempt"
fi
COMMON=(--campaign-root "$SEAL/M" --t "$T" --cap-s "$CAP_S" --no-outcome "$NO_OUTCOME" --final "$FINAL" --out "$SEAL/out" --overhead "$OVERHEAD" --fidelity-rows "$FIDELITY_ROWS"
        --inspection-labels "$INSPECTION" "${INS[@]}" "${H3T[@]}" --campaign-tree "$CAMPAIGN_TREE" "${CC[@]}")
touch "$SCAN_PAUSE" 2>/dev/null
stage cut RUN -m snapshot cut "${COMMON[@]}"; rc=$?
say "cut: $(tail -n 1 "$SEAL/logs/cut.out" 2>/dev/null | sed 's/ out=.*//')"
[ -z "$CAPPED_ON" ] || say "capped correction: $(python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); print("applied", d.get("capped_applied"), "put back from their own store", d.get("capped_put_back"), "held aside", d.get("capped_held_aside"), "MISSING", d.get("capped_missing"))' "$SEAL/out/work/cut/cut.json" 2>&1 | tail -n 1)"
[ -z "$CAPPED_ON" ] || python3 -I -c 'import json,sys; sys.exit(1 if json.load(open(sys.argv[1])).get("capped_missing") else 0)' "$SEAL/out/work/cut/cut.json" || say "WARNING (FLAG): the capped correction could not be applied to some run(s) (capped_missing>0 in cut.json): the primary does NOT carry them"
[ $rc -eq 0 ] || { say "cut FAILED: $(tail -n 2 "$SEAL/logs/cut.err" | cut -c1-300)"; finish 5; }

# ---- 5. pipeline assemble + analysis (snapshot analyse: both; the split below is from its own log's stamps) ---------------------------------------------------------------
MM=(); [ -z "${MAX_MISSES:-}" ] || MM=(--max-planned-misses "$MAX_MISSES")
# the exact list now (the early pass read the run dirs that were done then; this one the cut's own, with the pipeline caches' entries)
if [ "${PREWARM:-1}" = 1 ]; then
  stage prewarm python3 -I "$V/launch/prewarm.py" --list "$SEAL/out/work/cut/run_dirs.txt" --threads "${PREWARM_THREADS:-48}" --extra "$CACHE_MAIN" "$CACHE_B" || say "WARNING: prewarm did not complete (the analysis still runs, cold)"
  sed 's/^/  /' "$SEAL/logs/prewarm.out" 2>/dev/null | cut -c1-200
fi
# keep-warm (lane-snap6, the lead 5 Nov): the analysis walks the providers one after the other and the page cache the prewarm filled is evicted by other readers before the later providers are reached (measured 5 Nov: main
# 0.08 s/run fingerprint right after the prewarm, the site_a stores 1.3-2.9 s/run). While an analysis runs, a niced background loop re-reads the cut's run dirs every KEEPWARM_PERIOD_S (4 min); a pass over cached
# files is cheap. prewarm.py changes nothing on disk. KEEPWARM=0 switches it off. Not in the analysis path: the fingerprint, the keys and pcache.py are untouched.
keepwarm_start() {   # $1: the cut's run_dirs.txt; sets KW_PID
  KW_PID=
  [ "${KEEPWARM:-1}" = 1 ] && [ -s "$1" ] || return 0
  rm -f "$SEAL/.keepwarm.stop"
  ( while [ ! -e "$SEAL/.keepwarm.stop" ]; do
      sleep "${KEEPWARM_PERIOD_S:-240}"; [ ! -e "$SEAL/.keepwarm.stop" ] || break
      nice -n 19 python3 -I "$V/launch/prewarm.py" --list "$1" --threads "${KEEPWARM_THREADS:-16}" >> "$SEAL/logs/keepwarm.out" 2>&1
    done ) > /dev/null 2>&1 < /dev/null &
  KW_PID=$!
}
keepwarm_stop() { touch "$SEAL/.keepwarm.stop"; [ -z "${KW_PID:-}" ] || { pkill -TERM -P "$KW_PID" 2>/dev/null; kill "$KW_PID" 2>/dev/null; wait "$KW_PID" 2>/dev/null; }; KW_PID=; }
keepwarm_start "$SEAL/out/work/cut/run_dirs.txt"
stage analyse RUN "${SNAPCLI[@]}" analyse "${COMMON[@]}" --providers "$SEAL/bmerge.json" --jobs "$JOBS" --worker-gib "$WORKER_GIB" "${MM[@]}"; rc=$?
keepwarm_stop
say "analyse: $(tail -n 1 "$SEAL/logs/analyse.out" 2>/dev/null | sed 's/ out=.*//')"
# ROUTE D, the PRIMARY tables (science #34 03:30Z, option B): the same cut as out/ (with the capped correction), the frozen table functions on the primary frame plus the K rows of the capped runs, TABLE-ONLY (the pipeline of out/ reused; kaug_wrap.py). out/ stays the frozen result beside. KAUG=1 (a switch of final-flags.env)
rck=1
if [ "${KAUG:-0}" = 1 ] && [ -n "${CAPPED_ON:-}" ] && [ $rc -eq 0 ]; then
  K1=("${COMMON[@]/#$SEAL\/out/$SEAL/out-kaug}")
  stage cut_kaug RUN -m snapshot cut "${K1[@]}"; rck=$?
  if [ $rck -eq 0 ]; then KAUG_SRC_OUT="$SEAL/out" stage analyse_kaug RUN "$V/launch/kaug_wrap.py" analyse "${K1[@]}" --providers "$SEAL/bmerge.json" --jobs "$JOBS" --worker-gib "$WORKER_GIB" "${MM[@]}"; rck=$?; fi
  say "K-augmented PRIMARY tables (out-kaug/, the capped runs as K rows, no measures): $(tail -n 1 "$SEAL/logs/analyse_kaug.out" 2>/dev/null | sed 's/ out=.*//') rc=$rck; $(grep -h 'kaug_wrap:' "$SEAL/logs/analyse_kaug.err" 2>/dev/null | tail -n 1)"
fi
[ -z "${SNAP_SKIP_MAIN_MAX:-}" ] || say "$(skip_note "$SEAL/out/pipeline/manifest.json" "interim knob, out/") | $(tail -n 1 "$SEAL/out/work/knob.txt" 2>/dev/null || echo 'no knob line (planning did not run)')"
if [ -f "$SEAL/out/snapshot.log" ]; then
  note pipeline_analysis_split "$(python3 -I - "$SEAL/out/snapshot.log" <<'EOF'
import json, sys, datetime as dt, re
ev = {}
for l in open(sys.argv[1]):
    m = re.match(r"(\S+Z) (\w+):", l)
    if m:
        ev.setdefault(m.group(2), dt.datetime.fromisoformat(m.group(1).replace("Z", "+00:00")).timestamp())
out = {k: int(ev[k]) for k in ("cut", "pipeline", "analysis") if k in ev}
d = {}
if "cut" in ev and "pipeline" in ev: d["cut_to_pipeline_log_s"] = int(ev["pipeline"] - ev["cut"])
if "pipeline" in ev and "analysis" in ev: d["pipeline_log_to_analysis_log_s"] = int(ev["analysis"] - ev["pipeline"])
print(json.dumps(d))
EOF
)"
fi
[ $rc -eq 0 ] || { say "analyse FAILED rc=$rc: $(tail -n 2 "$SEAL/logs/analyse.err" | cut -c1-300)"; }
if [ -f "$SEAL/out/work/merge/assemble.json" ]; then
  note assemble_counts "$(python3 -I -c "
import json; a=json.load(open('$SEAL/out/work/merge/assemble.json'))['providers']
print(json.dumps({p: {k: v[k] for k in ('analysed','planned_hits','planned_misses') if k in v} for p, v in sorted(a.items())}))")"
  say "assemble: $(python3 -I -c "
import json; a=json.load(open('$SEAL/out/work/merge/assemble.json'))['providers']
print(' '.join(f'{p}:hits={v.get(\"planned_hits\")}/{v.get(\"analysed\")} misses={v.get(\"planned_misses\")}' for p, v in sorted(a.items())))")"
fi

# ---- 5a. the coding decisions (science's ruling, #34 22:55Z: `report.py --unseal` inside the snapshot path, mechanical, every interim and the final) and the analysis that takes them -----------
# UNSEAL_ENABLED=1 is set by the scheduler for the real interims; a direct run (a rehearsal, a check) leaves it 0 and never touches the coders' sealed answers. The decisions and everything derived
# from them stay in the sealed dir; only sub-stage names, seconds and return codes are printed. The first analysis (out/) is without coding; the second (out-coded/) takes the labels.
UNSEAL=${UNSEAL:-$V/launch/snapshot-interim-unseal.sh}
URC=0
if [ "${UNSEAL_ENABLED:-0}" != 1 ]; then
  URC=8; note unseal '"not run: UNSEAL_ENABLED is not 1 (a rehearsal or a check never unseals)"'; say "unseal: not run (UNSEAL_ENABLED=0)"
elif [ $rc -ne 0 ]; then
  URC=9; say "unseal: not run (the analysis failed)"
else
  if [ "$FINAL_MODE" = true ] && [ -z "${UNSEAL_NOT_BEFORE:-}" ] && [ -z "$RESUME_FROM" ]; then UNSEAL_NOT_BEFORE=$(date -u -d "$T" +%F)T09:40:00Z; fi        # the coders' stop (the lead, 5 Nov): their decisions are final from then
  if [ -n "${UNSEAL_NOT_BEFORE:-}" ]; then
    wsec=$(( $(date -u -d "$UNSEAL_NOT_BEFORE" +%s) - $(date +%s) ))
    if [ $wsec -gt 0 ]; then say "coding stop: waiting ${wsec}s until $UNSEAL_NOT_BEFORE before the unseal"; note unseal_wait_s "$wsec"; sleep "$wsec"; else say "coding stop ($UNSEAL_NOT_BEFORE) has passed"; fi
  fi
  if [ -n "$RESUME_FROM" ]; then URC=0; say "unseal: reused from $RESUME_FROM (the coders' answers as sealed there)"; python3 -I "$V/launch/filter_labels.py" "$SEAL/out/pipeline/scored_rows.jsonl" "$SEAL/inspection/labels.jsonl" "$SEAL/frozen/inspection-labels.jsonl" > "$SEAL/inspection/filter_rerun.out" 2>&1 && python3 -I "$V/launch/filter_labels.py" "$SEAL/out/pipeline/scored_rows.jsonl" "$SEAL/inspection/coverage.jsonl" "$SEAL/frozen/inspection-coverage.jsonl" > "$SEAL/inspection/coverage_filter_rerun.out" 2>&1 && say "unseal: the reused labels and coverage were filtered again against THIS run's scored rows: $(tail -n 1 "$SEAL/inspection/filter_rerun.out" | cut -c1-100); $(tail -n 1 "$SEAL/inspection/coverage_filter_rerun.out" | cut -c1-100)"; else stage unseal "$UNSEAL" "$T" "$SEAL"; URC=$?; fi
  CR=${CODER_REPLAY:-$WT/coder-replay-run/snapshot/coder-replay-stage.sh}; CRON=0
  if [ -x "$CR" ] && [ "${CODER_REPLAY_ON:-1}" = 1 ] && [ $URC -eq 0 ] && [ -f "$SEAL/inspection/decisions.json" ]; then
    CRON=1; stage coder_replay_start timeout --kill-after=30 "$(( ${REPLAY_PLAN_BUDGET_S:-900} + 300 ))" env -C "$WT/coder-replay-run" "$CR" start "$T" "$SEAL" || say "WARNING (FLAG): coder replay start rc=$? (not part of the exit status)"
  fi
  sed 's/^/  /' "$SEAL/logs/unseal.out" 2>/dev/null | cut -c1-200
  [ -f "$SEAL/inspection/stages.jsonl" ] && note unseal_substages "$(python3 -I -c "import json; print(json.dumps([json.loads(l) for l in open('$SEAL/inspection/stages.jsonl') if l.strip()]))")"
  if [ $URC -eq 0 ] && [ -f "$SEAL/frozen/inspection-labels.jsonl" ]; then
    COMMON2=(--campaign-root "$SEAL/M" --t "$T" --cap-s "$CAP_S" --no-outcome "$NO_OUTCOME" --final "$FINAL" --out "$SEAL/out-coded" --overhead "$OVERHEAD" --fidelity-rows "$FIDELITY_ROWS"
             --inspection-labels "$SEAL/frozen/inspection-labels.jsonl" --inspection-coverage "$SEAL/frozen/inspection-coverage.jsonl" "${H3T[@]}" --campaign-tree "$CAMPAIGN_TREE" "${CC[@]}")
    stage cut_coded RUN -m snapshot cut "${COMMON2[@]}"; rc2=$?
    say "cut_coded: $(tail -n 1 "$SEAL/logs/cut_coded.out" 2>/dev/null | sed 's/ out=.*//')"
    if [ $rc2 -eq 0 ]; then
      if [ "${PREWARM:-1}" = 1 ]; then stage prewarm_coded python3 -I "$V/launch/prewarm.py" --list "$SEAL/out-coded/work/cut/run_dirs.txt" --threads "${PREWARM_THREADS:-48}" --extra "$CACHE_MAIN" "$CACHE_B" || say "WARNING: prewarm before the coded analysis did not complete (it still runs)"; fi
      keepwarm_start "$SEAL/out-coded/work/cut/run_dirs.txt"
      stage analyse_coded RUN "${SNAPCLI[@]}" analyse "${COMMON2[@]}" --providers "$SEAL/bmerge.json" --jobs "$JOBS" --worker-gib "$WORKER_GIB" "${MM[@]}"; rc2=$?
      keepwarm_stop
      say "analyse_coded: $(tail -n 1 "$SEAL/logs/analyse_coded.out" 2>/dev/null | sed 's/ out=.*//')"
      rck2=1
      if [ "${KAUG:-0}" = 1 ] && [ -n "${CAPPED_ON:-}" ] && [ "${rck:-1}" -eq 0 ]; then
        K2=("${COMMON2[@]/#$SEAL\/out-coded/$SEAL/out-coded-kaug}")
        stage cut_coded_kaug RUN -m snapshot cut "${K2[@]}"; rck2=$?
        if [ $rck2 -eq 0 ]; then KAUG_SRC_OUT="$SEAL/out-coded" stage analyse_coded_kaug RUN "$V/launch/kaug_wrap.py" analyse "${K2[@]}" --providers "$SEAL/bmerge.json" --jobs "$JOBS" --worker-gib "$WORKER_GIB" "${MM[@]}"; rck2=$?; fi
        say "K-augmented PRIMARY coded tables (out-coded-kaug/): $(tail -n 1 "$SEAL/logs/analyse_coded_kaug.out" 2>/dev/null | sed 's/ out=.*//') rc=$rck2"
      fi
      [ -z "${SNAP_SKIP_MAIN_MAX:-}" ] || say "$(skip_note "$SEAL/out-coded/pipeline/manifest.json" "interim knob, out-coded/") | $(tail -n 1 "$SEAL/out-coded/work/knob.txt" 2>/dev/null || echo 'no knob line (planning did not run)')"
    fi
    [ $rc2 -eq 0 ] || { URC=10; say "the analysis with the coding decisions failed (rc=$rc2): logs/analyse_coded.err, sealed"; }
  fi
fi

rm -f "$SCAN_PAUSE" 2>/dev/null     # the fill may run again (the analyses are done)
# ---- 5b. per-cell run counts for science (cell_counts.csv: counts only) ------------------------------------------------------------------------------------------------
[ $rc -ne 0 ] || stage cell_counts python3 -I "$V/launch/cell_counts.py" "$SEAL" || say "WARNING: cell_counts.csv was not written (logs/cell_counts.err)"
# science (#34 11:33Z): each attempt's provider and the level in force at its start, for reading M by level: <seal>/run_level.csv (totals only here)
[ $rc -ne 0 ] || { stage run_level python3 -I "$V/launch/run_level.py" "$SEAL" || say "WARNING: run_level.csv was not written (logs/run_level.err)"; sed 's/^/  /' "$SEAL/logs/run_level.out" 2>/dev/null | cut -c1-200; }

# ---- 6. H3 measure (extract per audit store, then the pinned measure) -------------------------------------------------------------------------------------------------
H3RC=0
if [ -x "$H3" ]; then
  stage h3 "$H3" "$T" "$SEAL"; H3RC=$?
  # the stage's own stdout is counts and seconds only (see snapshot-interim-h3.sh): show it, and keep its sub-stage timings in timings.json
  sed 's/^/  /' "$SEAL/logs/h3.out" 2>/dev/null | cut -c1-240
  [ -f "$SEAL/h3/stages.jsonl" ] && note h3_substages "$(python3 -I -c "import json; print(json.dumps([json.loads(l) for l in open('$SEAL/h3/stages.jsonl') if l.strip()]))")"
  [ $H3RC -eq 0 ] || say "h3 stage rc=$H3RC (logs/h3.err, sealed)"
  # the records table, primary part (science #34 05:56Z): from h3/measure; soft; RECORDS_TABLE=0 off
  if [ "${RECORDS_TABLE:-1}" = 1 ] && [ -f "$V/launch/records_table.py" ] && [ -s "$SEAL/h3/measure/record.csv" ]; then
    stage records_primary bash -c "cd '$WT/snap-interim' && ICSA_DATA=$V PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 nice -n 10 '$V/bin/memcap' 3 '$PY' '$V/launch/records_table.py' '$SEAL' --part primary --out-dir '$SEAL/records-table' --tree '$WT/snap-interim'" || say "WARNING (FLAG): the records table (primary part) failed (rc=$?): a side table, not part of the exit status"
    sed 's/^/  /' "$SEAL/logs/records_primary.out" 2>/dev/null | cut -c1-220
  fi
  # the exclusion list in force (science 5 Nov 02:50Z, foreign_lines): each audit store's exclusions.applied.json kept in the seal, the total on the terminal (a count, no run key)
  say "H3 exclusions: $(python3 -I - "$V/snap-h3" "$SEAL" <<'PYX'
import glob, json, os, shutil, sys
tot = n = 0
os.makedirs(sys.argv[2] + "/h3/exclusions", mode=0o700, exist_ok=True)
for f in sorted(glob.glob(sys.argv[1] + "/*/exclusions.applied.json")):
    try:
        d = json.load(open(f))
    except Exception:
        continue
    n += 1; tot += sum(v for v in d.get("by_reason", {}).values() if isinstance(v, int))
    shutil.copyfile(f, f"{sys.argv[2]}/h3/exclusions/{os.path.basename(os.path.dirname(f))}.json")
print(f"leases marked not_observed:foreign_lines over all stores={tot} (stores with the file: {n})")
PYX
)"
else
  H3RC=127; note h3 '"not run: no H3 stage installed"'; say "h3: not run ($H3 is not installed)"
fi
# the status of the whole path: analysis first, then freshness (a mirror that is not fresh at t makes a snapshot of an older store), then H3. Nothing is reported as a good snapshot
# when a stage did not run or failed; every stage above still ran, so the sealed outputs of the rest exist.
# ---- 7. the layout stage (lane-layout, #34; science 5 Nov): layout_read per run, the H3 reading beside the primary, the own-layout-only analysis beside every contrast. Everything under <seal>/layout/.
# Optional until lane-layout's script is installed ($V/launch/snapshot-interim-layout.sh, executable): then it is part of the snapshot and a failure of it is exit 9.
LAYOUT=${LAYOUT:-$V/launch/snapshot-interim-layout.sh}; LRC=0
export LAYOUT_CACHE=${LAYOUT_CACHE:-$V/snap-layout-cache}     # lane-layout's per-run evidence cache (sealed, mode 700), kept warm by layout-cache-loop.sh; verified 5 Nov: 636 hits = the cold read's files byte for byte, a changed exclusion window misses exactly its runs
export LAYOUT_JOBS=${LAYOUT_JOBS:-8}        # layout read is the one stage linear in the runs (0.7 s/run at 4 workers on a loaded host; lane-layout and the lead, 5 Nov: 8 from the 12:00Z interim, 10-12 for the final)
if [ "$FINAL_MODE" = true ]; then emit -1; say "the primary tables, the coded labels and H3 are done: the report above is written before the layout stage (timings.json exit=-1 = partial)"; fi
if [ -x "$LAYOUT" ]; then
  if [ "$FINAL_MODE" = true ]; then
    LAYOUT_BUDGET_S=${LAYOUT_BUDGET_S:-$(( TS + 11700 - $(date +%s) ))}                  # the fixed snapshot's tables by t+2h at the latest (noon is the hard limit for 09:00Z)
    if [ "$LAYOUT_BUDGET_S" -gt 60 ]; then stage layout timeout --kill-after=30 "$LAYOUT_BUDGET_S" "$LAYOUT" "$T" "$SEAL"; LRC=$?
    else LRC=9; note layout '"not run: no time left (LAYOUT_BUDGET_S)"'; say "layout: not run, no time left"; fi
    [ $LRC -ne 124 ] || { note layout_timeout "$LAYOUT_BUDGET_S"; say "layout: stopped at its time box (${LAYOUT_BUDGET_S}s); what was written stays, the rest is not run"; LRC=9; }
  else
    stage layout "$LAYOUT" "$T" "$SEAL"; LRC=$?
  fi
  sed 's/^/  /' "$SEAL/logs/layout.out" 2>/dev/null | cut -c1-240
  # lane-layout's one word that must be loud (no option, no count by option): did a REST run read files the provider audit shows that the gate never served
  if grep -q 'it_happened=yes' "$SEAL/logs/layout.out" 2>/dev/null; then say "BYPASS: it happened (see $SEAL/layout/bypass.csv)"; note layout_bypass '"it happened"'; fi
  [ -f "$SEAL/layout/stages.jsonl" ] && note layout_substages "$(python3 -I -c "import json; print(json.dumps([json.loads(l) for l in open('$SEAL/layout/stages.jsonl') if l.strip()]))")"
else
  note layout '"not run: the layout stage is not installed"'; say "layout: not run ($LAYOUT is not installed)"
fi
# the records table, complete (adds the own-layout reading and the layout_read counts from the layout stage); soft
if [ "${RECORDS_TABLE:-1}" = 1 ] && [ -f "$V/launch/records_table.py" ] && [ -s "$SEAL/h3/measure/record.csv" ]; then
  stage records_all bash -c "cd '$WT/snap-interim' && ICSA_DATA=$V PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 nice -n 10 '$V/bin/memcap' 3 '$PY' '$V/launch/records_table.py' '$SEAL' --part all --out-dir '$SEAL/records-table' --tree '$WT/snap-interim'" || say "WARNING (FLAG): the records table (complete) failed (rc=$?): a side table, not part of the exit status"
  sed 's/^/  /' "$SEAL/logs/records_all.out" 2>/dev/null | cut -c1-220
fi
# lane-replay's numeric coder-replay side table (#34): LAST, optional, time-boxed, never part of the exit status. `start` (above, right after the unseal) plans and starts the site_a detection in the
# background; `collect` here, after the layout stage, waits for it up to its own deadline and writes <seal>/coder_replay/. Its exit codes: 0 clean, 8 no coding decisions, 9 a step failed, 10 degraded = a flag.
if [ "${CRON:-0}" = 1 ]; then
  export REPLAY_BUDGET_S=${REPLAY_BUDGET_S:-$([ "$FINAL_MODE" = true ] && echo 1800 || echo 900)}
  stage coder_replay_collect timeout --kill-after=30 "$(( REPLAY_BUDGET_S + 300 ))" env -C "$WT/coder-replay-run" "$CR" collect "$T" "$SEAL"; CRC=$?
  grep -h 'coder-replay result:' "$SEAL/logs/coder_replay_collect.out" 2>/dev/null | tail -n 1 | cut -c1-240 | sed 's/^/  /'
  [ $CRC -eq 0 ] || { note coder_replay_rc "$CRC"; say "WARNING (FLAG): coder replay rc=$CRC (8 no coding decisions, 9 a step failed, 10 degraded, 124 time box): not part of the exit status"; }
fi
# the second coder's kappa (lane-code76; the lead 6 Nov 03:5xZ): launch/kappa-addendum.sh copies the key from the 18:00Z-c seal (sha checked, a LOUD failure if missing or different), the returned answers and the handoff sheet as read, and runs lane-code76's script; a side table, never part of the exit status; the final only (SECOND_KAPPA=0 switches it off)
if [ "$FINAL_MODE" = true ] && [ "${SECOND_KAPPA:-1}" = 1 ]; then
  stage second_kappa bash "$V/launch/kappa-addendum.sh" "$SEAL" || say "WARNING (FLAG) LOUD: the second-coder kappa did not run or failed (rc=$?): read logs/second_kappa_addendum.out; it is a side table and not part of the exit status"
  sed 's/^/  /' "$SEAL/logs/second_kappa_addendum.out" 2>/dev/null | tail -n 3 | cut -c1-240
fi
# the paper's exhibits stage (lane-exhibits, 5 Nov): fail-soft, never part of the exit status; runs after the replay collect (coder_replay/coder_causes.csv exists only from then). Rerun by hand: EXH_BUDGET_S=1800 $EXH $T $SEAL
EXH=${EXHIBITS:-$V/launch/snapshot-interim-exhibits.sh}
if [ -x "$EXH" ] && [ $rc -eq 0 ]; then
  stage exhibits timeout --kill-after=30 "${EXH_STAGE_BUDGET_S:-420}" "$EXH" "$T" "$SEAL"; ERC=$?
  sed 's/^/  /' "$SEAL/logs/exhibits.out" 2>/dev/null | cut -c1-240
  [ $ERC -eq 0 ] || say "WARNING (FLAG): exhibits rc=$ERC (2 refused, 3 partial, 9 nothing, 75 memory, 124 time box): not part of the exit status; rerun by hand: EXH_BUDGET_S=1800 $EXH $T $SEAL"
fi
# PRIMARY.json (science #34 03:30Z, lane-snap6): ONE pointer at the seal root saying which table sets are the PRIMARY ones (out-kaug/ and out-coded-kaug/ when the K-augmented step ran, else the frozen out/ and out-coded/), the exact table note, the correction file's sha256 and the counts; the report and the exhibits read it
stage primary_json python3 -I "$V/launch/primary_json.py" "$SEAL" || say "WARNING (FLAG): PRIMARY.json could not be written (rc=$?): downstream readers must not guess which tables are primary"
sed 's/^/  /' "$SEAL/logs/primary_json.out" 2>/dev/null | cut -c1-240
# the fault-calibration score that was pulled (the lead 6 Nov 04:0xZ: whatever snap-fault/LATEST points at when the pull runs; its tag and age are printed), and the two side tables beside the primary fidelity read (science #34 04:02Z): the original 08:22Z score's invalid counts and a worst-case bound on the pulled score; soft, last
say "fault score pulled into the seal: tag $(cat "$SEAL/frozen/fault/fault.tag" 2>/dev/null || echo none); $(head -n 1 "$SEAL/frozen/fault/fault.age" 2>/dev/null || echo 'no age')"
if [ "${FIDELITY_EXTRA:-1}" = 1 ] && [ -s "$SEAL/frozen/fault/h3_table.csv" ] && [ -f "$V/launch/fidelity_extra.py" ]; then
  mkdir -p -m 700 "$SEAL/frozen/fault-original-0822Z" && cp -f "$V/snap-fault/20261105T082219Z/h3_table.csv" "$SEAL/frozen/fault-original-0822Z/h3_table.csv" 2>/dev/null
  stage fidelity_extra RUN "$V/launch/fidelity_extra.py" --latest "$SEAL/frozen/fault/h3_table.csv" --original "$SEAL/frozen/fault-original-0822Z/h3_table.csv" --latest-tag "$(cat "$SEAL/frozen/fault/fault.tag" 2>/dev/null || echo latest)" --out-dir "$SEAL/fidelity-extra" --t "$T" --final "$FINAL" || say "WARNING (FLAG): the fidelity side tables failed (rc=$?): a side table, not part of the exit status"
  sed 's/^/  /' "$SEAL/logs/fidelity_extra.out" 2>/dev/null | cut -c1-200
fi
# the bytes contrast (science #34 05:53Z and 06:01Z; ADDED AFTER SEEING THE DATA): the frozen contrast_one on log2 bytes_between_sites for the three option pairs in both layouts, Holm over the pairs of one layout: on the MEASURED UNITS first (every compared option measured, strictly, as layout/bytes-measured/units.csv), then on all runs with bytes known; a side table, soft, last (it needs the layout stage's units file); BYTES_CONTRAST=0 off
if [ "${BYTES_CONTRAST:-1}" = 1 ] && [ $rc -eq 0 ] && [ -f "$V/launch/bytes_contrast.py" ]; then
  mkdir -p -m 700 "$SEAL/side-added-after-data"
  stage bytes_contrast bash -c "cd '$TREE' && ICSA_DATA=$V PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 nice -n 10 '$V/bin/memcap' 4 '$PY' '$V/launch/bytes_contrast.py' '$SEAL' --out-measured '$SEAL/side-added-after-data/bytes_contrast_measured_units.csv' --out-all '$SEAL/side-added-after-data/bytes_contrast_all_runs_with_bytes_known.csv' --analysis out" || say "WARNING (FLAG): the bytes contrast failed (rc=$?): a side table, not part of the exit status"
  sed 's/^/  /' "$SEAL/logs/bytes_contrast.out" 2>/dev/null | cut -c1-300
fi
# the Q4 side table (science #34 06:07Z; ADDED AFTER SEEING THE DATA): the share of finished runs whose reported region/baseline/target differs from the analysed extent, per option x layout, nulls counted; soft, last; EXTENT_ACCOUNT=0 off
if [ "${EXTENT_ACCOUNT:-1}" = 1 ] && [ -f "$V/launch/extent_account.py" ] && [ -s "$SEAL/out-coded/pipeline/scored_rows.jsonl" -o -s "$SEAL/out/pipeline/scored_rows.jsonl" ]; then
  mkdir -p -m 700 "$SEAL/side-added-after-data"
  stage extent_account python3 -I "$V/launch/extent_account.py" "$SEAL" --out "$SEAL/side-added-after-data/extent_account_differs.csv" || say "WARNING (FLAG): the extent-account table failed (rc=$?): a side table, not part of the exit status"
  sed 's/^/  /' "$SEAL/logs/extent_account.out" 2>/dev/null | cut -c1-220
fi
# the capped-correction sensitivity (a) (science 6 Nov 03:13Z): the retries IN PLACE OF the capped attempts = the same inputs without the correction; a side table, failing soft, last; CAPPED_SENS=0 off
if [ -n "${CAPPED_ON:-}" ] && [ "${CAPPED_SENS:-1}" = 1 ] && [ $rc -eq 0 ]; then
  RT=(); skipn=0; for x in "${COMMON[@]}"; do if [ $skipn = 1 ]; then skipn=0; continue; fi; if [ "$x" = "--capped-correction" ]; then skipn=1; continue; fi; RT+=("$x"); done
  RT=("${RT[@]/#$SEAL\/out/$SEAL/out-retries}")
  stage cut_retries RUN -m snapshot cut "${RT[@]}"; rcr=$?
  if [ $rcr -eq 0 ]; then stage analyse_retries RUN "${SNAPCLI[@]}" analyse "${RT[@]}" --providers "$SEAL/bmerge.json" --jobs "$JOBS" --worker-gib "$WORKER_GIB" "${MM[@]}"; rcr=$?; fi
  say "retries in place of the capped attempts (out-retries/): $(tail -n 1 "$SEAL/logs/analyse_retries.out" 2>/dev/null | sed 's/ out=.*//') rc=$rcr (a side table: not part of the exit status)"
fi
# the Lab-504 sensitivity (science 6 Nov 03:13Z): the primary contrasts recomputed WITHOUT the flagged GLM runs (b/checkpoint-6c/flag-lab504-14.json, copied into frozen/), same cohort cut; a side table, failing soft, last; LAB504_SENS=0 off
if [ "${LAB504_SENS:-1}" = 1 ] && [ $rc -eq 0 ] && [ -s "$SEAL/frozen/flag-lab504-14.json" ]; then
  L504=("${COMMON[@]/#$SEAL\/out/$SEAL/out-lab504}" --exclude-runs "$SEAL/frozen/flag-lab504-14.json")
  stage cut_lab504 RUN -m snapshot cut "${L504[@]}"; rcl=$?
  if [ $rcl -eq 0 ]; then stage analyse_lab504 RUN "${SNAPCLI[@]}" analyse "${L504[@]}" --providers "$SEAL/bmerge.json" --jobs "$JOBS" --worker-gib "$WORKER_GIB" "${MM[@]}"; rcl=$?; fi
  say "Lab-504 sensitivity (out-lab504/, the flagged runs left out): $(tail -n 1 "$SEAL/logs/analyse_lab504.out" 2>/dev/null | sed 's/ out=.*//') rc=$rcl (a side table: not part of the exit status)"
fi
# the 00:50Z sensitivity (science 6 Nov 01:08Z): the same inputs as out/ at the DEFAULT cut (t - cap), beside the cohort-cut tables; last in the order
if [ -n "${COHORT_CUT:-}" ] && [ "${SENS_050:-1}" = 1 ] && [ $rc -eq 0 ]; then
  S050=("${COMMON[@]/#$SEAL\/out/$SEAL/out-050}")
  C050=(); skip=0; for x in "${S050[@]}"; do if [ $skip = 1 ]; then skip=0; continue; fi; if [ "$x" = "--cohort-cut" ]; then skip=1; continue; fi; C050+=("$x"); done
  stage cut_050 RUN -m snapshot cut "${C050[@]}"; rc050=$?
  if [ $rc050 -eq 0 ]; then stage analyse_050 RUN "${SNAPCLI[@]}" analyse "${C050[@]}" --providers "$SEAL/bmerge.json" --jobs "$JOBS" --worker-gib "$WORKER_GIB" "${MM[@]}"; rc050=$?; fi
  say "sensitivity at the default cut (out-050/): $(tail -n 1 "$SEAL/logs/analyse_050.out" 2>/dev/null | sed 's/ out=.*//') rc=$rc050 (a side table: not part of the exit status)"
fi
# NOTE-SENS.txt in each sensitivity directory present (lead 6 Nov): the frozen basis, no K-aug; the retries one also says its correction is off
for _d in out-retries out-lab504 out-050; do
  [ -d "$SEAL/$_d" ] || continue
  case $_d in
    out-retries) _t="out-retries/ is computed on the frozen basis WITHOUT the capped correction (the retries count in place of the capped attempts) and without K-aug: compare with out/ and out-coded/, not with the primary out-kaug/.";;
    out-lab504) _t="out-lab504/ is computed on the frozen basis, with the capped correction and without K-aug, the flagged Lab-504 runs left out: compare with out/ and out-coded/, not with the primary out-kaug/.";;
    out-050) _t="out-050/ is computed on the frozen basis, with the capped correction and without K-aug, at the default 00:50Z cut: compare with out/ and out-coded/, not with the primary out-kaug/.";;
  esac
  printf '%s\n' "$_t" > "$SEAL/$_d/NOTE-SENS.txt"; chmod 600 "$SEAL/$_d/NOTE-SENS.txt"
done
# PRIMARY.json again, now that the sensitivity directories exist (it lists which of them are complete)
stage primary_json python3 -I "$V/launch/primary_json.py" "$SEAL" || true
# the structure of the outputs (file and column names, key paths with types; no value, no count) for science: $SEAL/structure.md
[ $rc -ne 0 ] || stage structure bash -c "python3 -I '$V/launch/snapshot_structure.py' '$SEAL' > '$SEAL/structure.md'" || true
STATUS=$rc
if [ $STATUS -eq 0 ] && { [ $FM -ne 0 ] || [ $FB -ne 0 ] || [ ${FI:-1} -ne 0 ]; }; then STATUS=6; fi
if [ $STATUS -eq 0 ] && [ $H3RC -ne 0 ]; then STATUS=7; fi
if [ $STATUS -eq 0 ] && [ $URC -ne 0 ]; then STATUS=8; fi
if [ $STATUS -eq 0 ] && [ $LRC -ne 0 ]; then STATUS=9; fi
[ $STATUS -eq 0 ] || say "NOT A CLEAN SNAPSHOT: exit $STATUS (analysis rc=$rc; freshness main=$FM b=$FB inputs=${FI:-1}; h3 rc=$H3RC; unseal/coded analysis rc=$URC; layout rc=$LRC): 6 = a mirror or main's extract inputs not fresh at t, 7 = the H3 stage did not run clean, 8 = no coding decisions in this snapshot (UNSEAL_ENABLED not 1, or the unseal or the coded analysis failed), 9 = the layout stage did not run clean"
finish $STATUS
