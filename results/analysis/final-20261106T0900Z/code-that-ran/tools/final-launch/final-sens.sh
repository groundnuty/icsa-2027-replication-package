#!/usr/bin/env bash
# final-sens.sh <the finished 09:00Z seal> [tag, default sens] [--dry]   (lane-snap6, 6 Nov; science #34 09:20Z)
# The three heavy sensitivities on the final, by RESUME, AFTER its coded tables exist: out-retries, out-lab504, then out-050 (the 00:50Z cut LAST). Only those stages run (SKIP_MAIN=1): the cut and the analysis of each, on the copied frozen/, M/, inspection/; the main stages are reused.
# New dir <seal>-<tag> (final-20261106T0900Z-sens): the final's seal is never written. Flags: CAPPED_CORR=1 CAPPED_SENS=1 LAB504_SENS=1 SENS_050=1, KAUG=0 (no K-aug tables here), OVERHEAD_FINAL=1 (the same input as the final). Heavy: one analysis at a time, ~15 min each + cut/prewarm; do not start while another heavy job of the final runs.
set -u
V=/mnt/volume2/icsa-2027; ORIG=${1:?the finished seal}; TAG=${2:-sens}; DRY=0; for a in "$@"; do [ "$a" = --dry ] && DRY=1; done
ORIG=$(readlink -f "$ORIG"); B=$(basename "$ORIG"); NEW=$V/snapshots/$B-$TAG
case $B in final-*) PFX=final-; FIN=true;; interim-*) PFX=interim-; FIN=false;; *) echo "not a seal dir name: $B" >&2; exit 64;; esac
T=$(printf '%s' "${B#*-}" | sed -E 's/-r[0-9]*$//; s/^([0-9]{4})([0-9]{2})([0-9]{2})T([0-9]{2})([0-9]{2})Z$/\1-\2-\3T\4:\5:00Z/')
case $T in ????-??-??T??:??:??Z) ;; *) echo "cannot read t from $B" >&2; exit 64;; esac
[ -d "$ORIG/inspection" ] && [ -f "$ORIG/out-coded/tables/manifest.json" ] || { echo "REFUSED: $ORIG has no inspection/ or complete out-coded/ tables yet (the sensitivities come AFTER the coded tables)"; [ $DRY = 1 ] || exit 66; }
[ ! -e "$NEW" ] || { echo "REFUSED: $NEW exists"; exit 65; }
FF=$V/lane-snap6/final-flags-sens.env
printf '# the sensitivities-only resume (lane-snap6): heavy sensitivities ON, K-aug off\nCAPPED_CORR=1\nKAUG=0\nOVERHEAD_FINAL=1\nCAPPED_SENS=1\nLAB504_SENS=1\nSENS_050=1\n' > "$FF"
echo "sensitivities-only resume of $ORIG: t=$T new dir=$NEW flags=$(grep -v '^#' "$FF" | tr '\n' ' ')"
CMD="RESUME_FROM=$ORIG SKIP_MAIN=1 TAG_SUFFIX=-$TAG SEAL_PREFIX=$PFX FINAL=$FIN UNSEAL_ENABLED=1 FINAL_FLAGS_FILE=$FF bash $V/launch/snapshot-interim.sh $T"
[ $DRY = 1 ] && { echo "DRY: would run: $CMD"; exit 0; }
RESUME_FROM=$ORIG SKIP_MAIN=1 TAG_SUFFIX=-$TAG SEAL_PREFIX=$PFX FINAL=$FIN UNSEAL_ENABLED=1 FINAL_FLAGS_FILE=$FF setsid nohup bash $V/launch/snapshot-interim.sh $T > $V/snapshots/sched/run-$B-$TAG.log 2>&1 < /dev/null &
echo "started pid $!: log snapshots/sched/run-$B-$TAG.log"
