#!/usr/bin/env bash
# Writes the preflight STAMP that mplus-run.sh --run needs on .23: what only the lead's host can read. Run on THIS host, right before `mplus-run.sh --run`.
#   site_g solo:     site_g-solo-check.sh with CUTOFF = 3 minutes ago (reads site_g's audit log, one bounded tail, as the lead's tool does)
#   .8 idle:     no icsa process and no icsa-sbx container on .8 (read-only, through bin/vm2ssh)
#   site_f restart:  asserted by YOU with --site_f-restart-ok, once mplus.md's step 0 passed (HTTP 200, new opw.id, rss levelled, the two site_f-settings hashes equal)
# DRY by default: prints what it would run and reads nothing. `--write` reads site_g and .8 and writes $V/mplus/preflight-stamp.json on .23.
#   bash mplus-preflight-local.sh                          dry
#   bash mplus-preflight-local.sh --write --site_f-restart-ok  real
set -u
export SSH_AUTH_SOCK=
V=/mnt/volume2/icsa-2027; L=$V/launch; H23=198.51.100.2
write=0; site_f=false; for x in "$@"; do case "$x" in --write) write=1;; --site_f-restart-ok) site_f=true;; *) echo "usage: [--write] [--site_f-restart-ok]"; exit 64;; esac; done
K=(-o BatchMode=yes -o ConnectTimeout=12 -o IdentitiesOnly=yes -i ~/.secrets/icsa-2027/runvm_ed25519 -o UserKnownHostsFile=~/.secrets/icsa-2027/runvm_known_hosts)
CUT=$(date -u -d '3 minutes ago' '+%Y-%m-%d %H:%M:%S')
# the remote script goes in on stdin (no quoting through the bastion); docker's own exit code is reported, since a failing `docker ps` would otherwise read as zero containers
R8=$(cat <<'RS'
pgrep -af '[i]csa\.(campaign|scripted|instruments|faults|harness)' | cut -c1-120
d=$(docker ps --format '{{.Names}}' 2>&1); echo "docker_rc=$?"
echo "containers=$(printf '%s\n' "$d" | grep -c '^icsa-sbx-')"
RS
)
if [ $write -eq 0 ]; then
  echo "DRY (nothing read, nothing written). It would run, in this order:"
  echo "  CUTOFF='$CUT' bash $L/site_g-solo-check.sh        # reads site_g (audit log tail); SOLO is required"
  echo "  $V/bin/vm2ssh email-3@example 'bash -s' <<< (script below)      # .8 must show no process line, docker_rc=0 and containers=0"; echo "$R8" | sed 's/^/      /'
  echo "  site_f_restart_ok=$site_f  (you pass --site_f-restart-ok after mplus.md step 0)"
  echo "  ssh .23: write $V/mplus/preflight-stamp.json {utc, site_g_solo, host8_idle, site_f_restart_ok, cutoff, by}"
  exit 0
fi
out=$(CUTOFF="$CUT" bash "$L/site_g-solo-check.sh" 2>&1); rc=$?
echo "$out" | tail -n 8
case "$out" in *"NOT SOLO"*) solo=false;; *SOLO*) [ $rc -eq 0 ] && solo=true || solo=null;; *) solo=null;; esac
e8=$(mktemp); o8=$(printf '%s\n' "$R8" | "$V/bin/vm2ssh" email-3@example 'bash -s' 2>"$e8"); r8=$?
echo "--- .8 (rc $r8):"; echo "$o8" | tail -n 8; [ -s "$e8" ] && { echo "--- .8 stderr (not parsed):"; head -n 4 "$e8"; }; rm -f "$e8"
# idle only when stdout is exactly: docker_rc=0 and containers=0, no process line (stderr noise from ssh or the bastion does not count either way)
if [ $r8 -ne 0 ]; then idle8=null; elif [ "$(echo "$o8" | grep -c .)" -eq 2 ] && echo "$o8" | grep -qx 'docker_rc=0' && echo "$o8" | grep -qx 'containers=0'; then idle8=true; else idle8=false; fi
stamp=$(python3 -I -c "import json,sys,time; print(json.dumps({'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'site_g_solo': json.loads(sys.argv[1]), 'host8_idle': json.loads(sys.argv[2]), 'site_f_restart_ok': json.loads(sys.argv[3]), 'cutoff': sys.argv[4], 'by': 'mplus-preflight-local.sh'}))" "$solo" "$idle8" "$site_f" "$CUT")
echo "stamp: $stamp"
printf '%s\n' "$stamp" | ssh "${K[@]}" ubuntu@$H23 "mkdir -p $V/mplus && cat > $V/mplus/preflight-stamp.json.tmp && mv $V/mplus/preflight-stamp.json.tmp $V/mplus/preflight-stamp.json" && echo "written on .23"
