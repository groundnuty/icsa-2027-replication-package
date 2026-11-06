"""Break the pipeline one way at a time in a throwaway copy: does the test named notice?"""
import shutil, subprocess, sys
from pathlib import Path
SRC, DST = Path("/mnt/volume2/icsa-2027/wt/9p-pipe"), Path("/mnt/volume2/icsa-2027/wt/9p-mutp")
OLD = Path("/mnt/volume2/icsa-2027/wt/9p-shas/icsa/instruments/readext.py")
MUT = [
 ("icsa/pipeline/resources.py", "self.data_dir = Path(data_dir) if data_dir else Path(index_root or paths.DATA_ROOT) / s1_dir_name", "self.data_dir = Path(data_dir) if data_dir else None", "tests/pipeline/test_postrun.py", "test_production_recomputes", "the reference reads paths.S1_DIR again"),
 ("icsa/pipeline/postrun.py", 'in ("proxy.jsonl", "gate_requests.jsonl"):', 'in ("proxy.jsonl",):', "tests/pipeline/test_postrun.py", "test_a_real_d_run", "cut downloads from the local server's log only"),
 ("icsa/pipeline/postrun.py", 'decoded_not_delivered=_xcheck(lab, "decoded_not_delivered")', "decoded_not_delivered=None", "tests/pipeline/test_postrun.py", "test_a_real_m_run", "the M cross-check does not reach the coder"),
 ("icsa/pipeline/postrun.py", 'cells = next((c for c in (run_dir / "cells" / "cells.jsonl", run_dir / rec.code_cells_path) if c.is_file()), None)', "cells = next((c for c in (run_dir / rec.code_cells_path,) if c.is_file()), None)", "tests/pipeline/test_postrun.py", "test_the_sandbox_cell_log", "the harness copy of the code is scanned"),
 ("icsa/pipeline/postrun.py", 'listing_disagrees=_xcheck(lab, "listing_disagrees")', "listing_disagrees=None", "tests/pipeline/test_listing_seam.py", "", "the disagreement does not reach the coder"),
 ("icsa/causes/rules.py", "if ev.listing is None or ev.listing_disagrees:", "if ev.listing is None:", "tests/pipeline/test_listing_seam.py", "", "a disputed listing still concludes recovery"),
 ("icsa/pipeline/resources.py", "self._index = load_full_index(self.index_root)", "from icsa.instruments.layout import LayoutIndex as _L; self._index = _L.load(__import__('icsa.instruments.fullindex').instruments.fullindex.index_dir(self.index_root) / 'index.npz', shas_from_caller=True)", "tests/pipeline/test_real_index.py", "test_the_campaigns_index", "a bare load of the real index"),
 (None, None, None, "tests/pipeline/test_real_index.py", "test_a_real_run", "the old to_units, every unit in memory"),
]
caught = 0
for f, a, b, t, k, why in MUT:
    if DST.exists(): shutil.rmtree(DST)
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns(".venv", "__pycache__", "results", "evidence", ".pytest_cache"), symlinks=True)
    if f is None:
        shutil.copy(OLD, DST / "icsa/instruments/readext.py")
    else:
        p = DST / f; s = p.read_text(); assert a in s, a; p.write_text(s.replace(a, b))
    cmd = [str(SRC / ".venv/bin/python"), "-m", "pytest", t, "-q", "-x", "--no-header", "-p", "no:cacheprovider", "--basetemp=/mnt/volume2/icsa-2027/pytest-tmp/lane-9p-mutp"] + (["-k", k] if k else [])
    r = subprocess.run(cmd, cwd=DST, capture_output=True, text=True, env={"PYTHONPATH": str(DST), "PATH": "/usr/bin:/bin", "HOME": "~"})
    last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]
    caught += r.returncode == 1
    print(("CAUGHT" if r.returncode == 1 else f"MISSED rc={r.returncode}"), "|", why, "|", last[:80], flush=True)
shutil.rmtree(DST)
print(f"caught {caught} of {len(MUT)}")
