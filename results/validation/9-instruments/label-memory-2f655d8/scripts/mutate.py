"""Break the fix on purpose, one way at a time, in a throwaway copy: does tests/instruments/test_units_tally.py notice?"""
import shutil, subprocess, sys
from pathlib import Path
SRC, DST = Path("/mnt/volume2/icsa-2027/wt/9p-mem2"), Path("/mnt/volume2/icsa-2027/wt/9p-mut2")
MUT = [
 ("units.py", "cells = np.bitwise_or(np.frombuffer(old, np.uint8), np.frombuffer(cells, np.uint8)).tobytes()", "pass", "a day's second piece overwrites the first"),
 ("units.py", "out += total - in_box if d in required else total", "out += total", "beyond counts required cells in the box"),
 ("units.py", "out += total - in_box if d in required else total", "out += total - in_box", "beyond ignores a day outside the periods"),
 ("units.py", "if d in wanted and self._counted(cells)[1])", "if d in wanted)", "an extent keeps a day with nothing in the box"),
 ("units.py", "m[lat[sel], lon[sel]] = True", "m[lat, lon] = True", "units leak across days"),
 ("layout.py", "min(int(o) + c, n)", "int(o) + c", "a chunk past the shape is not clipped"),
 ("layout.py", "(starts[first] <= off[wk]) & (ends[first] >= off[wk] + size[wk])", "np.ones(wk.size, bool)", "a touched chunk counts as whole"),
 ("layout.py", "whole = (fmask != 0) if not fl.filtered else np.ones(off.size, bool)\n    wk = np.nonzero(whole & touched)", "whole = np.ones(off.size, bool)\n    wk = np.nonzero(whole & touched)", "an unfiltered chunk read in part counts as filtered"),
 ("layout.py", "    partial = np.nonzero(~whole & touched)[0]\n", "    partial = np.empty(0, np.int64)\n", "chunks read in part are dropped"),
 ("layout.py", "(ends[first] >= off[wk] + size[wk])", "(ends[first] >= off[wk] + size[wk] - 1)", "a chunk one byte short at its end counts as whole"),
 ("layout.py", "(starts[first] <= off[wk]) &", "(starts[first] <= off[wk] + 1) &", "a chunk one byte short at its start counts as whole"),
 ("layout.py", "lo = np.searchsorted(ends, off, side=\"right\")", "lo = np.searchsorted(ends, off, side=\"left\")", "the read that stops at a chunk's first byte counts as touching it"),
 ("layout.py", "(ends[first] >= off[wk] + size[wk])", "(ends[np.minimum(first + 1, ends.size - 1)] >= off[wk] + size[wk])", "two separate reads count as one across a gap"),
 ("readext.py", "beyond_days = sorted((set(tally.days) | named_days) - required)", "beyond_days = sorted(set(tally.days) - required)", "days known by name only are dropped"),
]
caught = 0
for f, a, b, why in MUT:
    if DST.exists(): shutil.rmtree(DST)
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns(".venv", "__pycache__", "results", "evidence", ".pytest_cache"), symlinks=True)
    p = DST / "icsa/instruments" / f; s = p.read_text()
    assert a in s, a
    p.write_text(s.replace(a, b))
    r = subprocess.run([str(SRC / ".venv/bin/python"), "-m", "pytest", "tests/instruments/test_units_tally.py", "-q", "-x", "--no-header", "-p", "no:cacheprovider", "--basetemp=/mnt/volume2/icsa-2027/pytest-tmp/lane-9p-mut"], cwd=DST, capture_output=True, text=True, env={"PYTHONPATH": str(DST), "PATH": "/usr/bin:/bin"})
    last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]
    caught += r.returncode == 1
    print(("CAUGHT" if r.returncode == 1 else f"MISSED rc={r.returncode}"), "|", why, "|", last[:90], flush=True)
shutil.rmtree(DST)
print(f"caught {caught} of {len(MUT)}")
