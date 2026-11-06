#!/usr/bin/env bash
# hpc_tar_ages.sh <seal dir> <t epoch> : the age, against t, of every HPC provider's store tar on site_a scratch (state.sqlite.tar, refreshed by the exporter) and a label (lane-snap6, 6 Nov; the lead 06:2xZ). ONE read-only ssh (stat), no data read.
# Writes <seal>/frozen/hpc-store-tar-ages.txt: `provider<TAB>tar_mtime_utc<TAB>age_vs_t_s<TAB>label`. icsa-site_a-14..19: "live store unreadable (job step limit), idle since 5 Nov 17:34Z" (the lead's wording); the others: the exporter's last write.
set -u
SEAL=${1:?seal dir}; TS=${2:?t epoch}
V=/mnt/volume2/icsa-2027; CFG=~/.secrets/icsa-2027/site_a-b/config; SCR=/net/scratch/site_bb/user_1/user_1/site_r/hpc
OUT=$SEAL/frozen/hpc-store-tar-ages.txt; mkdir -p -m 700 "$SEAL/frozen"
. "$V/launch/lib-providers.sh"; load_providers
HP=""; for p in $PROVIDERS; do [ "${VIA[$p]:-}" = site_a ] && HP="$HP $p"; done
RAW=$(timeout 120 ssh -F "$CFG" -o BatchMode=yes host-27.invalid "for p in $HP; do printf '%s %s\n' \$p \$(stat -c %Y $SCR/\$p/state.sqlite.tar 2>/dev/null || echo none); done" 2>/dev/null)
[ -n "$RAW" ] || { echo "hpc-tar-ages: the stat over ssh gave nothing: NO ages recorded"; exit 1; }
printf '%s\n' "$RAW" | python3 -I "$V/launch/hpc_tar_ages.py" "$TS" "$OUT"
