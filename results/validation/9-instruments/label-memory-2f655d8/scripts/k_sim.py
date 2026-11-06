"""One K local-sim case at a time through the real Sandbox: real gate, real tracer, the image's real platform client, MockOnedata on the local copy with site_g's real ids. Nothing on site_g. Stops before K's own label (this checkout's labeller is the old one)."""
import json, sys, time
from pathlib import Path
from icsa.inspection import krun
from icsa.harness import real_sandbox as rs
IMAGE = "sha256:ec24a9ff20c1acb4e8c7cafe4f994551bacd1ead03a43bc747cd5dc518ef2f0a"
WANT = "d7ca5cfbe936401c86b58d7affca42a7e0f4cb2a7f185973b64555b7640e9c67"
cases, out, stub = map(Path, sys.argv[1:4]); ids = [a for a in sys.argv[4:] if not a.startswith("--")]
t = time.time(); krun.prepare_stub(stub); print("stub ready", round(time.time() - t, 1), flush=True)
ins = rs.ensure_instruments(); print("instruments", ins[2], flush=True); assert ins[2] == WANT
for cid in ids:
    t = time.time()
    row = krun.run_case(cases / cid, out, image_id=IMAGE, instruments=ins, stub_root=stub, label_fn=lambda d, c: {"label": "not labelled here"})
    print(cid, round(time.time() - t, 1), json.dumps({k: row.get(k) for k in ("run_dir", "infra", "wall_s", "data_path", "memory_peak_bytes", "oom_killed", "instruments_sha256", "image_id")}), flush=True)
