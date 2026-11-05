#!/usr/bin/env bash
# The kernel's hung-task lines of the run hosts, copied into an interim's seal at the freeze (lane-snap, #34; lane-layout's contract, science 5 Nov 05:06Z: max_read_gap_s / hung_task_lines of M runs).
#   kernel_hung_pull.sh <seal dir>      -> <seal>/frozen/kernel-hung/<store>__<host>.log and <store>__<host>.log.since
# <store> is the audit store's name (site_g, site_u, ...), <host> the audit record's `host` field: site_g's store has `.23` and `.8`, a B provider's is empty, written `-`. HPC (site_a) nodes have none (unknown).
# .log = the stdout of `journalctl -k -b all -o short-iso --no-pager | grep -A12 "blocked for more"` ON THAT HOST (-b all: a reboot does not drop earlier lines); .log.since = the first kernel-journal
# timestamp there (a lease that starts before it is unknown to the reader, not zero). EMPTY IS A VALUE (ssh and journalctl worked, no match: the file exists and is empty); UNREADABLE IS UNKNOWN (ssh or
# journalctl failed, or the journal's first line is not a timestamp: NO file). Every file is written to a temp name and renamed. A host shared by stores (one VM runs several providers) is read once.
# Read-only on every host (journalctl as ubuntu, in group adm). Prints the files written, the hosts unreadable and the number of hung-task lines per file; exit 1 when any host was unreadable.
set -u
export SSH_AUTH_SOCK=
V=/mnt/volume2/icsa-2027
SEAL=${1:?seal dir}
. "$V/launch/lib-providers.sh"; load_providers
K=~/.secrets/icsa-2027/runvm_ed25519; KH=~/.secrets/icsa-2027/runvm_known_hosts
D=$SEAL/frozen/kernel-hung; mkdir -p -m 700 "$D"; umask 077
T=$(mktemp -d "${TMPDIR:-/tmp}/kernel-hung.XXXXXX"); trap 'rm -rf "$T"' EXIT
# the remote command: SINCE <first timestamp>, a marker, then the grep's output (grep rc 1 = no match = success: the `true`)
REMOTE='J=$(journalctl -k -b all -o short-iso --no-pager 2>/dev/null) || exit 3; f=$(printf "%s\n" "$J" | head -n1 | cut -d" " -f1); case $f in [0-9][0-9][0-9][0-9]-[0-9][0-9]-*) ;; *) exit 4;; esac; printf "SINCE %s\n=====LOG=====\n" "$f"; printf "%s\n" "$J" | grep -A12 "blocked for more"; true'
declare -A OK
fetch() {       # key, then the ssh command words
  local key=$1; shift
  [ -z "${OK[$key]:-}" ] || return 0
  if timeout 150 "$@" "$REMOTE" > "$T/$key.raw" 2> "$T/$key.err" && [ "$(head -n1 "$T/$key.raw" | cut -c1-6)" = "SINCE " ] && grep -qx '=====LOG=====' "$T/$key.raw"; then OK[$key]=1; else OK[$key]=0; fi
}
put() {         # store, host label, key
  local name=$1__$2 key=$3 since
  if [ "${OK[$key]:-0}" != 1 ]; then echo "kernel-hung: $name UNKNOWN (host unreadable: $(tail -n 1 "$T/$key.err" 2>/dev/null | cut -c1-100))"; return 1; fi
  since=$(head -n1 "$T/$key.raw" | cut -d' ' -f2)
  sed '1,/^=====LOG=====$/d' "$T/$key.raw" > "$D/.$name.log.tmp" && mv -f "$D/.$name.log.tmp" "$D/$name.log" || return 1
  printf '%s\n' "$since" > "$D/.$name.log.since.tmp" && mv -f "$D/.$name.log.since.tmp" "$D/$name.log.since" || return 1
  echo "kernel-hung: $name since=$since hung_task_lines=$(grep -c 'blocked for more than' "$D/$name.log")"
}
rc=0
SSH_B=(ssh -n -o BatchMode=yes -o ConnectTimeout=10 -o IdentitiesOnly=yes -i "$K" -o UserKnownHostsFile="$KH")
# site_g's store: the run hosts .23 and .8
fetch h23 "${SSH_B[@]}" email-1@example
fetch h8 "$V/bin/vm2ssh" email-3@example
put site_g .23 h23 || rc=1
put site_g .8 h8 || rc=1
# each B provider (a vm2 host is .8 again): its own host's journal, the audit record's host field being empty
for p in $PROVIDERS; do
  [ "${VIA[$p]:-}" != site_a ] || continue
  h=${HOST[$p]}; key=h$h
  if [ "${VIA[$p]:-}" = vm2 ]; then key=h8; else fetch "$key" "${SSH_B[@]}" "ubuntu@$h"; fi
  put "$p" - "$key" || rc=1
done
exit $rc
