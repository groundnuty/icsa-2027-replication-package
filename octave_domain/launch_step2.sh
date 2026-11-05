#!/bin/bash
# Run the named shards of Step_2 at once on this node (inside a step of a Slurm job), each in its own Apptainer process, and wait.
# usage: launch_step2.sh <shard name> ...      (columns come from shards/shards.txt: "name ja jb")
D=/net/scratch/site_bb/user_1/user_1/icsa-octave-domain
for n in "$@"; do
  read -r name ja jb < <(grep "^$n " $D/shards/shards.txt)
  [ "$name" = "$n" ] || { echo "no shard $n in shards.txt"; exit 2; }
  bash $D/src/octave_domain/run_shard.sh $n $ja $jb 12 &
done
wait
