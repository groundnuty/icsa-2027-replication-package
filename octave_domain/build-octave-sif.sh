#!/bin/bash
# runs ON a compute node inside a step: unpack the amd64 image of the docker-save archive into node tmpfs, build one SIF; only the SIF goes to scratch
set -eu
S=/net/scratch/site_bb/user_1/user_1/icsa-octave-domain
B=/tmp/octave-build-$USER; rm -rf $B; mkdir -p $B/tmp $B/layout
export APPTAINER_CACHEDIR=$B/cache APPTAINER_TMPDIR=$B/tmp TMPDIR=$B/tmp
date -u +%T
tar xf $S/image/octave-9.2.0.save.tar -C $B/layout
# the archive's index is an OCI image index (100d394c...); the amd64 manifest it lists is what is unpacked
python3 - <<PY
import hashlib, json
L = "$B/layout"
idx = json.load(open(L + "/blobs/sha256/100d394c57b86469748d26ddafcf73a1074338a66dabcababe2e4e05146772b9"))
raw = open(L + "/blobs/sha256/100d394c57b86469748d26ddafcf73a1074338a66dabcababe2e4e05146772b9", "rb").read()
assert hashlib.sha256(raw).hexdigest() == "100d394c57b86469748d26ddafcf73a1074338a66dabcababe2e4e05146772b9"
amd = [m for m in idx["manifests"] if m.get("platform", {}).get("architecture") == "amd64"][0]
mb = open(L + "/blobs/sha256/" + amd["digest"].split(":")[1], "rb").read()
assert "sha256:" + hashlib.sha256(mb).hexdigest() == amd["digest"]
json.dump({"schemaVersion": 2, "manifests": [{"mediaType": amd["mediaType"], "digest": amd["digest"], "size": amd["size"], "annotations": {"org.opencontainers.image.ref.name": "octave"}}]}, open(L + "/index.json", "w"))
print("amd64 manifest", amd["digest"])
PY
python3 $S/src/octave_domain/ociunpack.py $B/layout octave $B~fs > $S/image/octave.unpack.json
date -u +%T; find $B~fs | wc -l; du -sh $B~fs
apptainer build --force $B/octave.sif $B~fs
date -u +%T
cp $B/octave.sif $S/image/octave.sif.part && mv $S/image/octave.sif.part $S/image/octave.sif
rm -rf $B
ls -la $S/image/octave.sif
sha256sum $S/image/octave.sif
