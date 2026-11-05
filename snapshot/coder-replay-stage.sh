#!/usr/bin/env bash
# The coder-replay side table of an interim snapshot (lane-replay, #34; science 5 Nov 11:09Z, comment 6656480476): the coders' exact extractions replayed against the frozen detector.
#   coder-replay-stage.sh [start|collect|both] <t> <seal dir>        (default: both; after the unseal sub-stage: it reads <seal>/inspection/{decisions.json,population.jsonl})
#     start    plan on this host (who is replayed, which extents are new), then the detection on the site_a holder jobs IN THE BACKGROUND (time-boxed); returns at once
#     collect  waits for it up to the deadline, imports what came back, writes <seal>/coder_replay/coder_replay.csv and meta.json
#     both     start, then collect, in one call
# Everything written is under <seal>/coder_replay/ (sealed, mode 700: coder_replay.csv, coder_causes.csv, meta.json, work/) and the cache $REPLAY_CACHE (700). Outcome values are only in the CSV and the cache; stdout is totals and seconds.
# Never blocks or fails the primary: a stage that cannot run says why on stdout and exits non-zero. EXIT CODES: 0 clean; 8 no coding decisions in the seal (the unseal sub-stage did not run); 9 a step failed
# (plan, collect); 10 DEGRADED: the table exists, but some runs that could be replayed were not because the computation did not deliver (site_a unreachable, the time box, a failed job, a truth mismatch).
# The result line `coder-replay result: replayed=N not_replayed=M degraded=K ...` is the one line to log; stdout is otherwise totals and seconds. Per run, the table says why.
# Budgets: REPLAY_PLAN_BUDGET_S (default 900 s) for the plan, which is cold only once; REPLAY_BUDGET_S (default 900 s) from the end of the plan to the end of collect; the site_a side keeps inside it and
# is killed (by process group, from its pid) at the deadline. Optional: REPLAY_SKIP_REMOTE=1 plans and collects with what the cache holds (no compute).
set -u
export SSH_AUTH_SOCK=
MODE=both
case "${1:-}" in start|collect|both) MODE=$1; shift;; esac
T=${1:?t}; SEAL=${2:?seal dir}
V=/mnt/volume2/icsa-2027
WT=~/work/wt
# NOT `TREE`/`PY`: the driver uses those names for its own tree (snap-run), which has no snapshot.coderreplay. The pinned checkout and the fill venv are this stage's own.
TREE=${REPLAY_TREE:-$WT/coder-replay-run}                         # a PINNED (detached) checkout of feat/34-coder-replay; its code sha is in meta.json
PY=${REPLAY_PY:-$WT/fill-09ecc2c0/.venv/bin/python}
CACHE=${REPLAY_CACHE:-$V/snap-coder-replay-cache}
ANSWERS=${CODERS_SEALED:-$V/snapshots/coding/sealed}
BUDGET_S=${REPLAY_BUDGET_S:-900}
PLAN_BUDGET_S=${REPLAY_PLAN_BUDGET_S:-900}
MEMCAP=${MEMCAP:-2}
OUT=$SEAL/coder_replay; WORK=$OUT/work
umask 077
mkdir -p -m 700 "$OUT" "$WORK" "$CACHE"
STAGES=$OUT/stages.jsonl
case "$OUT" in "$SEAL"/*) ;; *) echo "coder-replay: output outside the seal: refused" >&2; exit 2;; esac
[ -s "$SEAL/inspection/decisions.json" ] && [ -s "$SEAL/inspection/population.jsonl" ] || { echo "coder-replay: no coding decisions in this seal (the unseal sub-stage did not run): not run"; exit 8; }
memgate() {
  local deadline=$(( $(date +%s) + 300 )) a
  while :; do
    a=$(awk '/MemAvailable/{printf "%d", $2/1048576}' /proc/meminfo)
    [ "$a" -ge $(( MEMCAP + 4 )) ] && return 0
    [ "$(date +%s)" -lt "$deadline" ] || { echo "memgate: MemAvailable ${a}GiB < $(( MEMCAP + 4 ))GiB for 300s: refused"; return 75; }
    sleep 10
  done
}
py() { memgate || return 75; ( cd "$TREE" && PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 ICSA_DATA=$V nice -n 10 "$V/bin/memcap" "$MEMCAP" "$PY" -B "$@" ); }
sub() {      # sub NAME CMD...: stdout/stderr into $OUT/NAME.{out,err}; one JSON line in stages.jsonl; prints name, rc, seconds and the last stdout line (counts only)
  local name=$1; shift
  local s0 s1 rc
  s0=$(date +%s.%N)
  "$@" > "$OUT/$name.out" 2> "$OUT/$name.err" < /dev/null; rc=$?
  s1=$(date +%s.%N)
  python3 -I -c 'import json,sys; n,a,b,rc=sys.argv[1:5]; print(json.dumps({"substage":n,"seconds":round(float(b)-float(a),1),"rc":int(rc)}))' "$name" "$s0" "$s1" "$rc" >> "$STAGES"
  echo "coder-replay $name rc=$rc seconds=$(python3 -I -c "print(round($s1-$s0,1))") $(tail -n 1 "$OUT/$name.out" | cut -c1-200)"
  return $rc
}
rc_all=0
if [ "$MODE" = start ] || [ "$MODE" = both ]; then
  rm -f "$WORK/remote.json" "$WORK/remote.pid"; rm -rf "$WORK/results" "$WORK/tmp"
  memgate || { echo "coder-replay: not enough memory for the plan: not run"; exit 9; }
  sub plan timeout -k 20 "$PLAN_BUDGET_S" env PYTHONPATH="$TREE" PYTHONDONTWRITEBYTECODE=1 ICSA_DATA=$V nice -n 10 "$V/bin/memcap" "$MEMCAP" "$PY" -B -m snapshot.coderreplay plan "$SEAL" --answers-root "$ANSWERS" --cache "$CACHE" \
    || { echo "coder-replay: plan failed or exceeded $PLAN_BUDGET_S s (stderr in $OUT/plan.err, sealed)"; exit 9; }
  START=$(date +%s); echo "$START" > "$WORK/start.epoch"; echo $(( START + BUDGET_S )) > "$WORK/deadline.epoch"        # the budget of the rest starts when the plan is done
  if [ "${REPLAY_SKIP_REMOTE:-0}" = 1 ]; then
    echo '{"skipped": true, "time_box": false}' > "$WORK/remote.json"
  elif [ -s "$WORK/jobs.jsonl" ]; then
    # the site_a side, in the background; its own budget ends 120 s before the stage's, for the import and the table
    cd "$TREE" || exit 9
    PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 ICSA_DATA=$V setsid nohup nice -n 10 "$V/bin/memcap" "$MEMCAP" "$PY" -B -m snapshot.coderreplay_remote run "$SEAL" --budget-s $(( BUDGET_S - 120 )) \
        > "$OUT/remote.out" 2> "$OUT/remote.err" < /dev/null &
    echo $! > "$WORK/remote.pid"           # setsid: this pid leads its own process group, which is what the deadline kills
    echo "coder-replay start: the detection runs in the background (pid $(cat "$WORK/remote.pid"), deadline $(date -u -d @"$(cat "$WORK/deadline.epoch")" +%H:%M:%SZ))"
  else
    echo '{"jobs": 0, "time_box": false}' > "$WORK/remote.json"; echo "coder-replay start: nothing to compute (every extent is in the cache)"
  fi
fi
if [ "$MODE" = collect ] || [ "$MODE" = both ]; then
  [ -s "$WORK/items.jsonl" ] || { echo "coder-replay: collect without a start (no $WORK/items.jsonl): not run"; exit 9; }
  DL=$(cat "$WORK/deadline.epoch" 2>/dev/null || echo $(( $(date +%s) + 60 )))
  while [ ! -f "$WORK/remote.json" ] && [ "$(date +%s)" -lt "$DL" ]; do sleep 5; done
  if [ ! -f "$WORK/remote.json" ]; then       # past the deadline and not done: stop it (its process group, by pid), wait a moment, then take what came back whole
    echo "coder-replay: the detection did not finish by the deadline: stopping it and collecting what came back"
    if [ -s "$WORK/remote.pid" ]; then rp=$(cat "$WORK/remote.pid"); kill -TERM -- "-$rp" 2>/dev/null || kill -TERM "$rp" 2>/dev/null; for _ in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$rp" 2>/dev/null || break; sleep 1; done; kill -KILL -- "-$rp" 2>/dev/null; fi
    echo '{"time_box": true, "killed": true}' > "$WORK/remote.json"
  fi
  RES=(); [ -d "$WORK/results" ] && RES=(--results "$WORK/results")
  sub collect py -m snapshot.coderreplay collect "$SEAL" --cache "$CACHE" --t "$T" "${RES[@]}"; crc=$?
  [ $crc -eq 0 ] || [ $crc -eq 10 ] || { echo "coder-replay: collect failed rc=$crc (stderr in $OUT/collect.err, sealed)"; exit 9; }
  # the rule-based causes of the runs the coders resolved to omitting (host only, from the coders' extents; a failure here does not touch the table above). stdout: seconds, no count.
  CAUSES=ok
  sub causes py -m snapshot.codercauses "$SEAL" --answers-root "$ANSWERS" --t "$T" || { CAUSES=failed; echo "coder-replay: causes failed (stderr in $OUT/causes.err, sealed); the replay table is unaffected"; }
  [ -s "$OUT/coder_causes.csv" ] || CAUSES=failed
  echo "coder-replay: the table is $OUT/coder_replay.csv, the causes $OUT/coder_causes.csv (sealed)"
  # THE LAST LINE the stage prints (a logger that keeps `tail -n 1` keeps this): the counts, and the word DEGRADED when computable runs were not replayed. Under 160 characters.
  python3 -I -c '
import json,sys
m=json.load(open(sys.argv[1])); b=m["not_replayed_by_reason"]
print("coder-replay result:%s rows=%d replayed=%d not_replayed=%d degraded=%d unavailable=%d timebox=%d failed=%d truth=%d causes=%s final=%s" % (" DEGRADED" if m["degraded"] else "", m["rows"],m["replayed"],m["not_replayed"],m["degraded"],b.get("compute_unavailable",0),b.get("time_box",0),b.get("compute_failed",0),b.get("truth_mismatch",0),sys.argv[2],m["final"]))' "$OUT/meta.json" "$CAUSES"
  [ $crc -eq 10 ] && exit 10
fi
exit $rc_all
