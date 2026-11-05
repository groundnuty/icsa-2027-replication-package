#!/usr/bin/env bash
# Build the Octave work dir for the #4 equivalence run: the authors' m_mhw detectc.m (never edited
# in place) patched with detectc_octave.patch, plus the shims and the block runner.
# Usage: tools/octave/prepare.sh <work dir>   (reads ${ICSA_DATA:-/mnt/volume2/icsa-2027}/ref/m_mhw)
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
work="$1"
orig="${ICSA_DATA:-/mnt/volume2/icsa-2027}/ref/m_mhw/detectc.m"
mkdir -p "$work"
patch --quiet -o "$work/detectc.m" "$orig" < "$here/detectc_octave.patch"
cp "$here"/movmean_omitnan.m "$here"/nanmax.m "$here"/nansum.m "$here"/run_block.m "$here"/t_semantics.m "$work"/
( cd "$(dirname "$orig")" && echo "m_mhw commit: $(cat COMMIT 2>/dev/null || echo unknown)"; sha256sum detectc.m ) > "$work/PROVENANCE"
sha256sum "$work"/*.m >> "$work/PROVENANCE"
cat "$work/PROVENANCE"
