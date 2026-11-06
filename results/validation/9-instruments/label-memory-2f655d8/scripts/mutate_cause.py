"""Break the code one way at a time in a throwaway copy: does the cause-input comparison, on real logs, notice? Failure means a failed hand-worked check, or an output that differs from the good run."""
import json, shutil, subprocess
from pathlib import Path
SRC, DST = Path("/mnt/volume2/icsa-2027/wt/9p-mem2"), Path("/mnt/volume2/icsa-2027/wt/9p-mutc")
L = Path("/mnt/volume2/icsa-2027/scratch-9p/task1")
MUT = [
 ("crosscheck.py", "got, _ = _delivered_chunks(fl, merged, rel, READAHEAD_BYTES.get(option, 0))", "got, _ = _delivered_chunks(fl, merged, rel, 0)", "stub", "T's read-ahead not trimmed"),
 ("crosscheck.py", "if ts and not any_bytes:\n                not_delivered.append(rel)", "if False:\n                not_delivered.append(rel)", "stub", "a decoded file no log delivered is not reported (S1)"),
 ("crosscheck.py", "if any_bytes and not ts:\n                not_decoded.append(rel)", "if False:\n                not_decoded.append(rel)", "stub", "a delivered file nothing decoded is not reported (S1)"),
 ("crosscheck.py", "missing = sorted(ts - got_all)", "missing = []", "stub", "a decoded chunk no log delivered is not reported (S2)"),
 ("labeller.py", "read = dataclasses.replace(read, beyond_days=sorted(set(read.beyond_days) | (known - req_days)))", "pass", "stub", "T's fetch outside the required days is not in read_beyond_days"),
 ("labeller.py", "beyond_days = sorted((s1_days | named | downloaded) - required)", "beyond_days = []", "stub", "read_beyond_days loses what the ledger decoded"),
 ("layout.py", "(starts[first] <= off[wk]) & (ends[first] >= off[wk] + size[wk])", "np.ones(wk.size, bool)", "slice", "to_units: a chunk touched at its edge counts as covered"),
 ("layout.py", "min(int(o) + c, n)", "min(int(o) + c - 1, n)", "slice", "to_units: a covered chunk loses its last cells"),
]
good = {m: json.loads((L / f"cause-9p-mem2-{m}.json").read_text()) for m in ("stub", "slice")}
caught = 0
for f, a, b, mode, why in MUT:
    if DST.exists(): shutil.rmtree(DST)
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns(".venv", "__pycache__", "results", "evidence", ".pytest_cache", "tests"), symlinks=True)
    p = DST / "icsa/instruments" / f; s = p.read_text(); assert a in s, a; p.write_text(s.replace(a, b))
    out = L / "cause-mut.json"; out.unlink(missing_ok=True)
    r = subprocess.run([str(SRC / ".venv/bin/python"), str(L / "cause_inputs.py"), mode, str(out)], cwd=DST, capture_output=True, text=True, env={"PYTHONPATH": str(DST), "PATH": "/usr/bin:/bin", "HOME": "~"})
    fails = [x for x in r.stdout.splitlines() if x.startswith("FAIL")]
    differs = out.is_file() and json.loads(out.read_text()) != good[mode]
    ok = bool(fails or differs or r.returncode not in (0, 1))
    caught += ok
    print(("CAUGHT" if ok else "MISSED"), "|", why, "|", mode, "| hand checks failed", len(fails), "| output differs", differs, "| rc", r.returncode, (r.stderr[-160:] if r.returncode not in (0, 1) else ""), flush=True)
shutil.rmtree(DST)
print(f"caught {caught} of {len(MUT)}")
