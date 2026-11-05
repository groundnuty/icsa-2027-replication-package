#!/bin/bash
# Run one shard of the whole-domain Octave job inside the Apptainer image, on the node this script runs on.
# usage: run_shard.sh <name> <ja> <jb> <virtual memory cap GB>        (ja..jb: columns of Step_1's 449 x 379 layout, 1-based)
set -u
D=/net/scratch/site_bb/user_1/user_1/icsa-octave-domain
name=$1; ja=$2; jb=$3; vm=${4:-24}
out=$D/shards/$name; mkdir -p $out
export APPTAINER_TMPDIR=/tmp/ap-$USER-$name APPTAINER_CACHEDIR=/tmp/ap-$USER/c
export APPTAINERENV_OMP_NUM_THREADS=1 APPTAINERENV_OPENBLAS_NUM_THREADS=1 APPTAINERENV_MKL_NUM_THREADS=1
mkdir -p $APPTAINER_TMPDIR
ulimit -v $((vm * 1024 * 1024))
cd /
echo "start $(date -u +%FT%TZ) host $(hostname) cols $ja..$jb vmem-cap ${vm}GB" > $out/octave.log
nice -n 19 /usr/bin/time -v apptainer exec --containall --no-home \
  --bind $D/work:/work:ro,$D/src/octave_domain:/tools:ro,$D/pack:/pack:ro,$out:/out \
  $D/image/octave.sif octave-cli --eval "ja=$ja;jb=$jb;run('/tools/run_shard.m')" >> $out/octave.log 2> $out/time.log
rc=$?
echo "exit $rc $(date -u +%FT%TZ)" >> $out/octave.log
rm -rf $APPTAINER_TMPDIR
if [ $rc -eq 0 ]; then ( cd $out && sha256sum m90.f64 mclim.f64 mhw_ts.f64 > outputs.sha256 ); fi
exit $rc
