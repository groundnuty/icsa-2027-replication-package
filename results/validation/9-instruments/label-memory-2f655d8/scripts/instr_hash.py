"""The hash of the instruments directory, as #76's current_instruments_sha256 computes it: built by
sandbox_dir.build_instruments_dir from this tree, hashed by real_sandbox.instruments_hash."""
import sys, tempfile
from pathlib import Path
from icsa.harness.real_sandbox import instruments_hash
from icsa.instruments import sandbox_dir
import icsa
print("icsa from:", icsa.__file__)
with tempfile.TemporaryDirectory(dir="/mnt/volume2/icsa-2027/scratch-9p") as t:
    d, _ = sandbox_dir.build_instruments_dir(Path(t) / "instruments")
    h = instruments_hash(d)
want = "d7ca5cfbe936401c86b58d7affca42a7e0f4cb2a7f185973b64555b7640e9c67"
print("computed:", h); print("required:", want); print("MATCH" if h == want else "MISMATCH")
sys.exit(0 if h == want else 1)
