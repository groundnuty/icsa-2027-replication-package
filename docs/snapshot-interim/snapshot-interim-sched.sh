#!/usr/bin/env bash
# Runs the interim snapshots at their times (lane-snap, #34; science 4 Nov 18:49Z): 5 Nov 00:00Z, 06:00Z, 12:00Z, 18:00Z and 6 Nov 00:00Z, one after the other, each by
# snapshot-interim.sh <t>. WRITTEN, NOT STARTED: nothing is scheduled until the lead says `start`.
#   snapshot-interim-sched.sh start | stop | status | list
# The 6 Nov 00:00Z entry is an interim snapshot like the others (--final false). The paper's fixed snapshot (amendment 43: 6 Nov 09:00Z, cohort cut 00:50Z) is the last entry, FINAL_TIME, run with --final true into final-<t>.
# Every scheduled interim runs with UNSEAL_ENABLED=1 (science, #34 22:55Z: report.py --unseal inside each interim); a direct run of the driver does not.
# One detached loop (setsid nohup); a failed snapshot is logged and the loop goes on to the next time; a time already past when the loop starts is skipped (logged).
set -u
V=/mnt/volume2/icsa-2027
TIMES=${TIMES:-"2026-11-05T00:00:00Z 2026-11-05T06:00:00Z 2026-11-05T12:00:00Z 2026-11-05T18:00:00Z 2026-11-06T00:00:00Z"}
FINAL_TIME=${FINAL_TIME:-2026-11-06T09:00:00Z}          # the paper's fixed snapshot (amendment 43: snapshot 6 Nov 09:00Z, cohort cut 00:50Z = t - 490 min): --final true, sealed dir final-<t>. snapshot/cut.py refuses it unless its FINAL_T is this instant; then nothing is made and the log says so
HERE=${HERE:-$V/snapshots/sched}
mkdir -p -m 700 "$HERE"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "$(ts) $*" >> "$HERE/sched.log"; }
running() { [ -s "$HERE/pid" ] && kill -0 "$(cat "$HERE/pid")" 2>/dev/null; }
case ${1:-} in
  _loop)
    echo $$ > "$HERE/pid"
    trap 'log "sched: stopped by signal"; rm -f "$HERE/pid"; exit 0' TERM INT
    log "sched: started pid=$$ times: $TIMES"
    for t in $TIMES $FINAL_TIME; do
      want=$(date -u -d "$t" +%s) || { log "bad time $t"; continue; }
      now=$(date -u +%s)
      if [ "$now" -gt $(( want + 1800 )) ]; then log "$t: already past by $(( now - want ))s (skipped)"; continue; fi
      while [ "$(date -u +%s)" -lt "$want" ]; do sleep 20 & wait $!; done
      log "$t: starting"
      fin=false; pre=interim-; [ "$t" != "$FINAL_TIME" ] || { fin=true; pre=final-; }
      FINAL=$fin SEAL_PREFIX=$pre UNSEAL_ENABLED=1 bash "$V/launch/snapshot-interim.sh" "$t" > "$HERE/run-$(date -u -d "$t" +%Y%m%dT%H%MZ).log" 2>&1 < /dev/null; rc=$?
      log "$t: finished rc=$rc: $(tail -n 1 "$HERE/run-$(date -u -d "$t" +%Y%m%dT%H%MZ).log" | cut -c1-300)"
    done
    log "sched: all times done"; rm -f "$HERE/pid";;
  start)
    if running; then echo "already running, pid $(cat "$HERE/pid")"; exit 1; fi
    setsid nohup bash "$0" _loop > /dev/null 2>&1 < /dev/null &
    for _ in 1 2 3 4 5 6 7 8 9 10; do running && break; sleep 0.3; done
    if running; then echo "started, pid $(cat "$HERE/pid")"; else echo "did not start (see $HERE/sched.log)"; exit 1; fi;;
  stop) if running; then kill -TERM "$(cat "$HERE/pid")"; echo stopped; else echo "not running"; fi;;
  status) if running; then echo "running, pid $(cat "$HERE/pid")"; else echo "not running"; fi; tail -n 8 "$HERE/sched.log" 2>/dev/null | cut -c1-300;;
  list) for t in $TIMES $FINAL_TIME; do echo "$t$([ "$t" = "$FINAL_TIME" ] && echo ' FINAL') cut=$(date -u -d "@$(( $(date -u -d "$t" +%s) - 29400 ))" +%FT%TZ)"; done;;
  *) echo "usage: $0 start | stop | status | list" >&2; exit 64;;
esac
