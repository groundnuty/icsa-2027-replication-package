"""What a run's sandbox holds on its host's disk now (science, #2, 20:20Z; the lead, 2 Nov): the sparse images of its sandbox directory
(icsa.sandbox: work.img, trace.img, ...) and its gate's spool (gatelog/spool), by allocated blocks, and the largest whole-file transfer its gate has logged as
complete. A D run spools the whole file at the gate, then writes it into its work image, then the spool goes: the scheduler reserves its peak less this, until
its download is known complete. Only the newest directory counts: a leftover of an earlier attempt is already in the free space and says nothing about this one."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

GATE_LOG = "requests.jsonl"


def sandbox_prefix(run_key: str) -> str:
    """The sandbox directory name's prefix for a campaign run key (`<block>__<RunId.key()>`), as icsa.sandbox.Sandbox names it."""
    rid = run_key.split("__", 1)[1] if "__" in run_key else run_key
    return re.sub(r"[^A-Za-z0-9_.-]", "_", rid)[:60] + "-"


def _allocated(p: Path) -> int:
    try:
        return os.stat(p).st_blocks * 512
    except OSError:
        return 0


def largest_transfer(gatelog: Path) -> int:
    """The largest transfer the gate logged as complete: status 200, with no error, its whole file fetched (`upstream_bytes`). A torn last line is not one."""
    best = 0
    try:
        with open(gatelog / GATE_LOG) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("status") == 200 and not r.get("error") and isinstance(r.get("upstream_bytes"), int):
                    best = max(best, r["upstream_bytes"])
    except OSError:
        pass
    return best


def sandbox_use(work_root: Path, run_key: str) -> dict | None:
    """{"bytes": images + spool, "spool_bytes": spool, "largest_transfer_bytes": ...} of the run's newest sandbox, or None when none is found."""
    try:
        dirs = [d for d in Path(work_root).iterdir() if d.name.startswith(sandbox_prefix(run_key)) and d.is_dir()]
    except OSError:
        return None
    if not dirs:
        return None
    d = max(dirs, key=lambda x: x.stat().st_mtime)
    images = spool = 0
    try:
        images = sum(_allocated(f) for f in d.iterdir() if f.is_file() and not f.is_symlink())   # never into a mount point
    except OSError:
        pass
    sp = d / "gatelog" / "spool"
    if sp.is_dir() and not os.path.ismount(sp):
        spool = sum(_allocated(f) for f in sp.iterdir() if f.is_file())
    return {"bytes": images + spool, "spool_bytes": spool, "largest_transfer_bytes": largest_transfer(d / "gatelog")}
