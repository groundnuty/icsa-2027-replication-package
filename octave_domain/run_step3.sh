#!/bin/bash
# Step_3 on the merged mhw_ts, inside the Apptainer image, on the node this script runs on.
# usage: run_step3.sh <out dir name under step3/> <shard list file in shards/> <virtual memory cap GB>
set -u
D=/net/scratch/site_bb/user_1/user_1/icsa-octave-domain
name=$1; list=$2; vm=${3:-90}
out=$D/step3/$name; mkdir -p $out
export APPTAINER_TMPDIR=/tmp/ap-$USER-s3-$name APPTAINER_CACHEDIR=/tmp/ap-$USER/c
export APPTAINERENV_OMP_NUM_THREADS=1 APPTAINERENV_OPENBLAS_NUM_THREADS=1 APPTAINERENV_MKL_NUM_THREADS=1
mkdir -p $APPTAINER_TMPDIR
ulimit -v $((vm * 1024 * 1024))
cd /
echo "start $(date -u +%FT%TZ) host $(hostname) list $list vmem-cap ${vm}GB" > $out/octave.log
nice -n 19 /usr/bin/time -v apptainer exec --containall --no-home \
  --bind $D/work:/work:ro,$D/src/octave_domain:/tools:ro,$D/shards:/shards:ro,$out:/out \
  $D/image/octave.sif octave-cli --eval "list='$list';run('/tools/run_step3.m')" >> $out/octave.log 2> $out/time.log
rc=$?
echo "exit $rc $(date -u +%FT%TZ)" >> $out/octave.log
rm -rf $APPTAINER_TMPDIR
if [ $rc -eq 0 ]; then ( cd $out && sha256sum events.txt events_mean_series.f64 > outputs.sha256 ); fi
exit $rc
