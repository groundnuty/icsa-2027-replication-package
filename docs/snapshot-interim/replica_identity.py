"""Prints the pcache key's code and resource identity as JSON (lane-snap, #34): run it on this host and on a remote replica, and the two outputs must be IDENTICAL for entries filled
there to be valid here.      cd <tree> && PYTHONPATH=. ICSA_DATA=/mnt/volume2/icsa-2027 python replica_identity.py PROVIDER
`code_identity()` (tree hash, tree data hash, pipeline hashes, parser_version, pcache.py hash, sys.version, numpy, pandas) and `resources_identity(Production(index_root, "s1z", None, data_dir))`
for the provider's own index and the data dir. Nothing about a run is read."""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from snapshot import pcache                     # noqa: E402
from icsa.pipeline.resources import Production  # noqa: E402

V = Path("/mnt/volume2/icsa-2027")
p = sys.argv[1]
res = Production(V / "snap-b-index" / p, "s1z", None, V / "s1z")
print(json.dumps({"code": pcache.code_identity(), "resources": pcache.resources_identity(res)}, indent=1, sort_keys=True, default=str))
