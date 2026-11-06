#!/usr/bin/env bash
# capped.sh <tag> <GiB> <seconds> <worktree-name> <script> [args...]: run a script under memcap on the VM with an RSS sampler OUTSIDE the cap's cgroup.
set -u
tag=$1; g=$2; secs=$3; wt=$4; shift 4
L=/mnt/volume2/icsa-2027/scratch-9p/task1; cd /mnt/volume2/icsa-2027/wt/$wt || exit 2
M=icsa9p-$tag-$$
t0=$(date +%s)
PATH=$HOME/.local/bin:$PATH PYTHONPATH=$PWD ICSA9P_MARK=$M /mnt/volume2/icsa-2027/bin/memcap "$g" timeout "$secs" .venv/bin/python -X faulthandler $L/wrap.py "$@" --mark=$M > $L/$tag.out 2> $L/$tag.err &
J=$!
: > $L/$tag.rss
while kill -0 $J 2>/dev/null; do
  P=$(pgrep -f -- "--mark=$M" | while read -r p; do c=$(tr '\0' ' ' </proc/$p/cmdline 2>/dev/null); case "$c" in .venv/bin/python*|*/python\ *) echo $p;; esac; done | tail -1)
  if [ -n "${P:-}" ] && [ -r /proc/$P/status ]; then
    printf '%s %s\n' "$(( $(date +%s)-t0 ))" "$(awk '/VmRSS/{r=$2}/VmHWM/{h=$2}END{printf "rss_gib=%.2f hwm_gib=%.2f",r/1048576,h/1048576}' /proc/$P/status)" >> $L/$tag.rss
  fi
  sleep 5
done
wait $J; rc=$?
echo "tag=$tag rc=$rc wall_s=$(( $(date +%s)-t0 )) peak_line=$(tail -1 $L/$tag.rss)" | tee -a $L/results.log
exit $rc
