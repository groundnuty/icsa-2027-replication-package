#!/usr/bin/env bash
# final-restart.sh stop [--dry] | start <stopped seal> [--dry]   (lane-snap6, 6 Nov; the lead's option (b): stop the 09:00Z analysis, put the missing entries in, restart the SAME t)
# stop : stops ONLY the 09:00Z driver (by its pid) and ITS analysis scopes (by cgroup scope), the keep-warm loop; leaves the H3 catch-up, late loop, memory guard, entry watcher, scheduler alone; renames the seal aside:
#        snapshots/final-20261106T0900Z -> snapshots/final-20261106T0900Z.stopped-<HHMM>-inline-misses (nothing is deleted).
# start: REFUSES unless the stopped seal exists and absent-entries ONLY=site_p (ABSENT_STORES to change) reads 0 (FORCE=1 overrides): the 09:00Z cut needs only db-0 main I48 D S1's entry; db-2's I10 M S1 retry entry is needed only by the out-retries sensitivity (the cut counts I10 through its capped attempt); then runs the driver in RESTART mode with the scheduler's own environment: new seal final-20261106T0900Z (the original name),
#        frozen/ and M/ reused, H3 catch-up pid taken from the running catch-up, everything after the merge fresh (unseal waits for 09:40Z). Log snapshots/sched/run-20261106T0900Z-restart.log.
set -u
V=/mnt/volume2/icsa-2027; L=$V/lane-snap6; SEAL=$V/snapshots/final-20261106T0900Z; T=2026-11-06T09:00:00Z
WT=~/work/wt
DRY=0; for a in "$@"; do [ "$a" = --dry ] && DRY=1; done
case ${1:-} in
  stop)
    DRV=$(pgrep -f "^bash $V/launch/snapshot-interim.sh $T\$" | head -n 1)
    echo "09:00Z driver pid: ${DRV:-NONE}"
    SCOPES=""; for p in $(pgrep -f -- "$SEAL/"); do [ "$p" = "$DRV" ] && continue; c=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null); case "$c" in *"-m snapshot"*|*kaug_wrap*|*prewarm.py*) sc=$(cut -d: -f3 /proc/$p/cgroup | awk -F/ '{print $NF}'); case "$sc" in run-r*.scope) SCOPES="$SCOPES $sc";; esac; echo "  process $p: ${c:0:100} (scope ${sc:-none})";; esac; done
    SCOPES=$(echo $SCOPES | tr ' ' '\n' | sort -u | tr '\n' ' '); echo "scopes of the 09:00Z run's heavy jobs: ${SCOPES:-none}"
    echo "H3 catch-up (left alone): $(pgrep -f 'h3-catchup.sh' | head -n 1)  late loop: $(cat $L/late-mirror/loop.pid 2>/dev/null)  memguard: $(cat $L/h3-memguard.pid 2>/dev/null)  entry watcher: $(cat $L/late-fill/watch.pid 2>/dev/null)"
    NEWNAME=$SEAL.stopped-$(date -u +%H%M)-inline-misses
    if [ $DRY = 1 ]; then echo "DRY: would $([ -n "$DRV" ] && echo "touch $SEAL/.keepwarm.stop, kill -TERM $DRV, systemctl --user stop ${SCOPES:-(none)}, then " )mv $SEAL $NEWNAME"; exit 0; fi
    if [ -z "$DRV" ]; then echo "no 09:00Z driver running (it has already ended): nothing to kill; the seal is only renamed aside"; [ -d "$SEAL" ] || { echo "no seal $SEAL either: nothing to do"; exit 1; }; mv "$SEAL" "$NEWNAME" && echo "seal kept as $NEWNAME"; exit 0; fi
    touch "$SEAL/.keepwarm.stop"; kill -TERM "$DRV"; sleep 2
    for sc in $SCOPES; do systemctl --user stop "$sc" && echo "stopped $sc"; done
    sleep 3; kill -0 "$DRV" 2>/dev/null && { echo "driver still alive: KILL"; kill -KILL "$DRV"; }
    mv "$SEAL" "$NEWNAME" && echo "seal kept as $NEWNAME"; exit 0;;
  start)
    ST=${2:?the stopped seal dir}; ST=$(readlink -f "$ST"); [ -d "$ST/frozen" ] && [ -d "$ST/M" ] || { echo "REFUSED: $ST is not a stopped seal (frozen/, M/)"; exit 66; }
    [ ! -e "$SEAL" ] || { echo "REFUSED: $SEAL exists: run stop first (the stopped seal is renamed aside)"; [ $DRY = 1 ] || exit 65; }
    CU=$(pgrep -f 'bash .*h3-catchup.sh' | head -n 1); echo "H3 catch-up pid: ${CU:-none (not running)}"
    out=$(cd $WT/snap-run && ONLY="${ABSENT_STORES:-site_p}" ICSA_DATA=$V PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 nice -n 12 $V/bin/memcap 6 $WT/fill-09ecc2c0/.venv/bin/python $L/build/absent-entries.py $V/snapshots/interim-20261106T0300Z-extra/bmerge.json 2>&1 | grep -E '^(icsa|site_g)[^ ]*: absent=|TOTAL')
    echo "$out"; if grep -q '^CAPPED_I48=1' ${FLAGS_FILE:-$L/final-flags.env} 2>/dev/null && [ "$(echo "$out" | grep -c ': absent=[1-9]')" = 1 ] && echo "$out" | grep -q 'site_p: absent=1 main__I48__D__S1__GLM-5.3-Flash__s1$'; then echo "CAPPED_I48=1 and I48 is the only absent entry: it is counted K by count (correction-unscorable-1.json): not a refusal"; else
echo "$out" | grep -q 'TOTAL absent=0' || { [ "${FORCE:-0}" = 1 ] || { echo "REFUSED: entries still absent (FORCE=1 overrides)"; exit 67; }; }; fi
    CMD="RESTART_FROM=$ST H3_CATCHUP_PID=$CU FINAL=true SEAL_PREFIX=final- UNSEAL_ENABLED=1 bash $V/launch/snapshot-interim.sh $T > $V/snapshots/sched/run-20261106T0900Z-restart.log"
    if [ $DRY = 1 ]; then echo "DRY: would run: $CMD"; exit 0; fi
    RESTART_FROM=$ST H3_CATCHUP_PID=${CU:-} FINAL=true SEAL_PREFIX=final- UNSEAL_ENABLED=1 setsid nohup bash $V/launch/snapshot-interim.sh $T > $V/snapshots/sched/run-20261106T0900Z-restart.log 2>&1 < /dev/null &
    echo "restart started pid $!: log snapshots/sched/run-20261106T0900Z-restart.log"; exit 0;;
  *) echo "usage: $0 stop [--dry] | start <stopped seal> [--dry]"; exit 64;;
esac
