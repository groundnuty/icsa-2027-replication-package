#!/usr/bin/env bash
# The fixed snapshot's own last fetch and pull, right after t (lane-snap, #34; the lead, 5 Nov 11:2xZ): a session that may be busy cannot promise them. Not a stop: any failure is a FLAG in the run's log
# (exit 1), the freeze goes on with what the loops fetched.
#   1. main's coding mirror: wait for a fetch that is already running (it began before this moment), then `mirrors.sh once coding` (the lead's own one-shot; TREE_LOCAL as its loop has it).
#   2. site_g's audit log into the incremental store: `tools/m_audit_loop.sh once` of lane-audit-run (one round with the loop's own settings; exit 6 = another puller holds the ledger: retried), the result
#      read from the loop's log lines it adds.
# Bounded: each step is limited, the whole thing ends within about 25 minutes at worst. Prints times and verdicts only.
set -u
export SSH_AUTH_SOCK=
V=/mnt/volume2/icsa-2027
WT=~/work/wt
ts() { date -u +%FT%TZ; }
rc=0
# 1. the coding mirror
for _ in $(seq 1 60); do pgrep -f 'snapshot.fetch .*--dest /mnt/volume2/icsa-2027/coding-mirror' > /dev/null || break; sleep 10; done
echo "$(ts) coding mirror: fetch now"
if TREE_LOCAL="${TREE_LOCAL:-$WT/frozen}" timeout 1200 bash "$V/launch/mirrors.sh" once coding; then
  l=$(grep 'coding: ' "$V/mirror-logs/mirrors.log" | tail -n 1)
  case "$l" in *"coding: ok"*) echo "$(ts) coding mirror: ok ($(echo "$l" | cut -d' ' -f1))";; *) echo "$(ts) coding mirror: FLAG: the last line is: $l"; rc=1;; esac
else echo "$(ts) coding mirror: FLAG: mirrors.sh once coding failed or timed out"; rc=1; fi
# 2. the audit pull
LOOPLOG=$V/m-audit/live/loop/loop.log
got=0
for i in 1 2 3 4 5 6 7 8; do
  n0=$(wc -l < "$LOOPLOG" 2>/dev/null || echo 0)
  timeout 900 bash "$WT/lane-audit-run/tools/m_audit_loop.sh" once > /dev/null 2>&1
  new=$(tail -n +$((n0 + 1)) "$LOOPLOG" 2>/dev/null)
  case "$new" in
    *"pull: ok"*) echo "$(ts) audit pull: ok (round $i)"; got=1; break;;
    *"another puller"*) echo "$(ts) audit pull: the ledger is held by another puller (round $i): retry in 20 s"; sleep 20;;
    *) echo "$(ts) audit pull: FLAG: round $i did not report ok: $(echo "$new" | tail -n 1 | cut -c1-160)"; break;;
  esac
done
[ $got -eq 1 ] || { echo "$(ts) audit pull: FLAG: no successful pull"; rc=1; }
exit $rc
