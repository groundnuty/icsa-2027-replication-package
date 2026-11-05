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
[ "$FINAL_MODE" != true ] || { JOBS=${JOBS_FINAL:-8}; MEMCAP=${MEMCAP_FINAL:-24}; }
OVERHEAD=${OVERHEAD:-none}; FIDELITY_ROWS=${FIDELITY_ROWS:-none}; INSPECTION=${INSPECTION:-none}
H3_TABLE=${H3_TABLE:-}                             # fault calibration's h3_table.csv (with FIDELITY_ROWS = its adapter_rows.jsonl): the fault-injection fidelity exhibit's verdicts; unset: the exhibit says tested=False
FREEZE_WAIT_S=${FREEZE_WAIT_S:-1500}               # how long to wait for main's mirror loop to fetch once after t
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
[ ! -e "$SEAL" ] || { echo "snapshot-interim: $SEAL exists: a snapshot is never overwritten (move it aside)" >&2; exit 65; }
umask 077
mkdir -p -m 700 "$SNAPS" && mkdir -m 700 "$SEAL" && mkdir -m 700 "$SEAL/logs" "$SEAL/frozen" "$SEAL/h3" || exit 65
STAGES=$SEAL/stages.jsonl
P0=$(date +%s)
now() { date -u +%FT%TZ; }
say() { echo "$(now) $*"; }
# stage NAME CMD...: runs CMD with stdout/stderr into logs/NAME.{out,err}, times it, appends one JSON line; returns CMD's rc
stage() {
  local name=$1; shift
  local s0 s1 rc
  s0=$(date +%s.%N)
  "$@" > "$SEAL/logs/$name.out" 2> "$SEAL/logs/$name.err" < /dev/null; rc=$?
  s1=$(date +%s.%N)
  python3 -I -c 'import json,sys; n,a,b,rc=sys.argv[1:5]; print(json.dumps({"stage":n,"start":float(a),"end":float(b),"seconds":round(float(b)-float(a),1),"rc":int(rc)}))' \
    "$name" "$s0" "$s1" "$rc" >> "$STAGES"
  say "stage $name rc=$rc seconds=$(python3 -I -c "print(round($s1-$s0,1))")"
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
  PAR=1 bash "$V/launch/b-mirrors.sh" once $PROVIDERS || { echo "at least one B fetch failed (the previous mirror of that store stands, and is not fresh)"; rc=1; }
  for p in $PROVIDERS; do
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
stage freeze_b freeze_b; FB=$?
# a dispatcher with a launch file (b/launch/icsa-*.json, b/launch-site_a/icsa-*.json) that is in no mirror is in no merge, no coding and no snapshot (icsa-site_a-1, 5 Nov 11:2xZ): say it loudly, note it in
# timings.json and the report. A launch file alone may be a plan not yet started (site_s, 5 Nov), so it is a flag, not a stop; a started one with no mirror is for the lead to read from this line.
UNMIRRORED=$(python3 -I - "$V" $PROVIDERS <<'PYU'
import glob, os, sys
V, have = sys.argv[1], set(sys.argv[2:])
exp = sorted({os.path.basename(f)[:-5] for d in ("b/launch", "b/launch-site_a") for f in glob.glob(f"{V}/{d}/icsa-*.json") if not f.endswith(".block.json")})
print(" ".join(e for e in exp if e not in have or not os.path.isfile(f"{V}/snap-b/{e}/state.sqlite")))
PYU
)
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
# the exclusion list in force (leases a foreign actor shared a slot user with: marked not_observed:foreign_lines), kept in the seal as it stood
cp -f "$V/lane-snap4/h3-exclusions.tsv" "$SEAL/frozen/h3-exclusions.tsv" 2>/dev/null || true
# main's extract inputs (the restart log, site_g's monitor log, the run hosts' quarantines): read-only copies from .23 and a check on .8, once per interim, at the freeze (the lead, 4 Nov)
stage freeze_inputs bash "$V/launch/h3-loop.sh" inputs; FI=$?
# the final: the loops that only feed later snapshots are stopped now (their running children finish), so the host's cores are the analysis's; the extract loop keeps going for the H3 catch-up
if [ "$FINAL_MODE" = true ] && [ "${QUIESCE:-1}" = 1 ]; then stage quiesce bash "$V/launch/quiesce-loops.sh" || true; fi
# the fixed snapshot's H3 catch-up (science: a run no pass reached reads not_observed:no_final_pass): one pass of every audit store now, in the background, while the analysis runs; the H3 stage waits for it
if [ "$FINAL_MODE" = true ] && [ "${H3_CATCHUP:-1}" = 1 ]; then
  bash "$V/launch/h3-catchup.sh" > "$SEAL/logs/h3_catchup.out" 2>&1 < /dev/null & export H3_CATCHUP_PID=$!
  export H3_CATCHUP_DEADLINE=${H3_CATCHUP_DEADLINE:-$(( TS + 6300 ))}       # t + 105 min: site_g's pass is the long one (about 45 min once the host is quiet)
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
    d = os.path.join(seal, "frozen", n); os.makedirs(d, mode=0o700)
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
COMMON=(--campaign-root "$SEAL/M" --t "$T" --cap-s "$CAP_S" --no-outcome "$NO_OUTCOME" --final "$FINAL" --out "$SEAL/out" --overhead "$OVERHEAD" --fidelity-rows "$FIDELITY_ROWS"
        --inspection-labels "$INSPECTION" "${INS[@]}" "${H3T[@]}" --campaign-tree "$CAMPAIGN_TREE")
stage cut RUN -m snapshot cut "${COMMON[@]}"; rc=$?
say "cut: $(tail -n 1 "$SEAL/logs/cut.out" 2>/dev/null | sed 's/ out=.*//')"
[ $rc -eq 0 ] || { say "cut FAILED: $(tail -n 2 "$SEAL/logs/cut.err" | cut -c1-300)"; finish 5; }

# ---- 5. pipeline assemble + analysis (snapshot analyse: both; the split below is from its own log's stamps) ---------------------------------------------------------------
MM=(); [ -z "${MAX_MISSES:-}" ] || MM=(--max-planned-misses "$MAX_MISSES")
# the exact list now (the early pass read the run dirs that were done then; this one the cut's own, with the pipeline caches' entries)
if [ "${PREWARM:-1}" = 1 ]; then
  stage prewarm python3 -I "$V/launch/prewarm.py" --list "$SEAL/out/work/cut/run_dirs.txt" --threads "${PREWARM_THREADS:-48}" --extra "$CACHE_MAIN" "$CACHE_B" || say "WARNING: prewarm did not complete (the analysis still runs, cold)"
  sed 's/^/  /' "$SEAL/logs/prewarm.out" 2>/dev/null | cut -c1-200
fi
stage analyse RUN -m snapshot analyse "${COMMON[@]}" --providers "$SEAL/bmerge.json" --jobs "$JOBS" --worker-gib "$WORKER_GIB" "${MM[@]}"; rc=$?
say "analyse: $(tail -n 1 "$SEAL/logs/analyse.out" 2>/dev/null | sed 's/ out=.*//')"
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
  if [ "$FINAL_MODE" = true ] && [ -z "${UNSEAL_NOT_BEFORE:-}" ]; then UNSEAL_NOT_BEFORE=$(date -u -d "$T" +%F)T09:30:00Z; fi        # the coders' stop (the lead, 5 Nov): their decisions are final from then
  if [ -n "${UNSEAL_NOT_BEFORE:-}" ]; then
    wsec=$(( $(date -u -d "$UNSEAL_NOT_BEFORE" +%s) - $(date +%s) ))
    if [ $wsec -gt 0 ]; then say "coding stop: waiting ${wsec}s until $UNSEAL_NOT_BEFORE before the unseal"; note unseal_wait_s "$wsec"; sleep "$wsec"; else say "coding stop ($UNSEAL_NOT_BEFORE) has passed"; fi
  fi
  stage unseal "$UNSEAL" "$T" "$SEAL"; URC=$?
  CR=${CODER_REPLAY:-$WT/coder-replay-run/snapshot/coder-replay-stage.sh}; CRON=0
  if [ -x "$CR" ] && [ "${CODER_REPLAY_ON:-1}" = 1 ] && [ $URC -eq 0 ] && [ -f "$SEAL/inspection/decisions.json" ]; then
    CRON=1; stage coder_replay_start timeout --kill-after=30 "$(( ${REPLAY_PLAN_BUDGET_S:-900} + 300 ))" "$CR" start "$T" "$SEAL" || say "WARNING (FLAG): coder replay start rc=$? (not part of the exit status)"
  fi
  sed 's/^/  /' "$SEAL/logs/unseal.out" 2>/dev/null | cut -c1-200
  [ -f "$SEAL/inspection/stages.jsonl" ] && note unseal_substages "$(python3 -I -c "import json; print(json.dumps([json.loads(l) for l in open('$SEAL/inspection/stages.jsonl') if l.strip()]))")"
  if [ $URC -eq 0 ] && [ -f "$SEAL/frozen/inspection-labels.jsonl" ]; then
    COMMON2=(--campaign-root "$SEAL/M" --t "$T" --cap-s "$CAP_S" --no-outcome "$NO_OUTCOME" --final "$FINAL" --out "$SEAL/out-coded" --overhead "$OVERHEAD" --fidelity-rows "$FIDELITY_ROWS"
             --inspection-labels "$SEAL/frozen/inspection-labels.jsonl" --inspection-coverage "$SEAL/frozen/inspection-coverage.jsonl" "${H3T[@]}" --campaign-tree "$CAMPAIGN_TREE")
    stage cut_coded RUN -m snapshot cut "${COMMON2[@]}"; rc2=$?
    say "cut_coded: $(tail -n 1 "$SEAL/logs/cut_coded.out" 2>/dev/null | sed 's/ out=.*//')"
    if [ $rc2 -eq 0 ]; then
      stage analyse_coded RUN -m snapshot analyse "${COMMON2[@]}" --providers "$SEAL/bmerge.json" --jobs "$JOBS" --worker-gib "$WORKER_GIB" "${MM[@]}"; rc2=$?
      say "analyse_coded: $(tail -n 1 "$SEAL/logs/analyse_coded.out" 2>/dev/null | sed 's/ out=.*//')"
    fi
    [ $rc2 -eq 0 ] || { URC=10; say "the analysis with the coding decisions failed (rc=$rc2): logs/analyse_coded.err, sealed"; }
  fi
fi

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
    LAYOUT_BUDGET_S=${LAYOUT_BUDGET_S:-$(( TS + 7200 - $(date +%s) ))}                  # the fixed snapshot's tables by t+2h at the latest (noon is the hard limit for 09:00Z)
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
# lane-replay's numeric coder-replay side table (#34): LAST, optional, time-boxed, never part of the exit status. `start` (above, right after the unseal) plans and starts the site_a detection in the
# background; `collect` here, after the layout stage, waits for it up to its own deadline and writes <seal>/coder_replay/. Its exit codes: 0 clean, 8 no coding decisions, 9 a step failed, 10 degraded = a flag.
if [ "${CRON:-0}" = 1 ]; then
  export REPLAY_BUDGET_S=${REPLAY_BUDGET_S:-$([ "$FINAL_MODE" = true ] && echo 1800 || echo 900)}
  stage coder_replay_collect timeout --kill-after=30 "$(( REPLAY_BUDGET_S + 300 ))" "$CR" collect "$T" "$SEAL"; CRC=$?
  grep -h 'coder-replay result:' "$SEAL/logs/coder_replay_collect.out" 2>/dev/null | tail -n 1 | cut -c1-240 | sed 's/^/  /'
  [ $CRC -eq 0 ] || { note coder_replay_rc "$CRC"; say "WARNING (FLAG): coder replay rc=$CRC (8 no coding decisions, 9 a step failed, 10 degraded, 124 time box): not part of the exit status"; }
fi
# the structure of the outputs (file and column names, key paths with types; no value, no count) for science: $SEAL/structure.md
[ $rc -ne 0 ] || stage structure bash -c "python3 -I '$V/launch/snapshot_structure.py' '$SEAL' > '$SEAL/structure.md'" || true
STATUS=$rc
if [ $STATUS -eq 0 ] && { [ $FM -ne 0 ] || [ $FB -ne 0 ] || [ ${FI:-1} -ne 0 ]; }; then STATUS=6; fi
if [ $STATUS -eq 0 ] && [ $H3RC -ne 0 ]; then STATUS=7; fi
if [ $STATUS -eq 0 ] && [ $URC -ne 0 ]; then STATUS=8; fi
if [ $STATUS -eq 0 ] && [ $LRC -ne 0 ]; then STATUS=9; fi
[ $STATUS -eq 0 ] || say "NOT A CLEAN SNAPSHOT: exit $STATUS (analysis rc=$rc; freshness main=$FM b=$FB inputs=${FI:-1}; h3 rc=$H3RC; unseal/coded analysis rc=$URC; layout rc=$LRC): 6 = a mirror or main's extract inputs not fresh at t, 7 = the H3 stage did not run clean, 8 = no coding decisions in this snapshot (UNSEAL_ENABLED not 1, or the unseal or the coded analysis failed), 9 = the layout stage did not run clean"
finish $STATUS
