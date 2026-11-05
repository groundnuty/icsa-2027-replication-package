"""The sandbox interface the harness codes against (#7 provides the real one).

`Sandbox.start(run_key, option, layout, data_config)`, `.exec(code, timeout_s) -> ExecResult`,
`.collect(dest_dir)` (writes dest_dir/output/{report.json,mhw_mask.nc}, dest_dir/cells, dest_dir/trace), `.metadata()`, `.stop()`.

`LocalSubprocessStandIn` below is a STAND-IN FOR TESTS ONLY: it runs each cell in a fresh local
Python subprocess in a temp dir. It enforces no data path, isolation or cache clearing, and must
never be used for a study run or as evidence about an option.
"""
from __future__ import annotations

import dataclasses
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Protocol

from icsa.records import Layout, Option


@dataclasses.dataclass
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_s: float
    kill: dict | None = None   # the cause of a kill or timeout, when the sandbox can tell (icsa.sandbox.killcause); None otherwise


class SandboxLike(Protocol):
    def exec(self, code: str, timeout_s: float) -> ExecResult: ...
    def collect(self, dest_dir: str | Path) -> None: ...
    def metadata(self) -> dict[str, Any]: ...
    def stop(self) -> None: ...


# (run_key, option, layout, data_config) -> started sandbox
SandboxFactory = Callable[[str, Option, Layout, dict], SandboxLike]


def real_sandbox_factory(image: str, pinned_image_id: str, time_cap_s: float, **kw) -> SandboxFactory:
    """The #7 sandbox as a harness `SandboxFactory`: pinned image, per-run tokens sized from the run's time cap,
    real configs (see `icsa.harness.real_sandbox`). There is no default image and no fallback to the stand-in."""
    from .real_sandbox import RealSandboxFactory
    return RealSandboxFactory(image, pinned_image_id, time_cap_s, **kw)


class LocalSubprocessStandIn:
    """STAND-IN (tests only). See the module docstring."""

    IS_STAND_IN = True

    def __init__(self, workdir: Path, data_config: dict | None = None):
        self.workdir = workdir
        (workdir / "output").mkdir(parents=True, exist_ok=True)
        self.data_config = data_config or {}
        self.stopped = False
        self.n_exec = 0

    @classmethod
    def start(cls, run_key: str, option: Option, layout: Layout, data_config: dict) -> "LocalSubprocessStandIn":
        sb = cls(Path(tempfile.mkdtemp(prefix="icsa-standin-")), data_config)
        sb.run_key, sb.option, sb.layout = run_key, option, layout
        return sb

    def exec(self, code: str, timeout_s: float) -> ExecResult:
        self.n_exec += 1
        t0 = time.monotonic()
        try:
            p = subprocess.run(
                [sys.executable, "-I", "-c", code], cwd=self.workdir, capture_output=True,
                text=True, timeout=timeout_s, errors="replace",
            )
            return ExecResult(p.stdout, p.stderr, p.returncode, time.monotonic() - t0)
        except subprocess.TimeoutExpired as e:
            def _s(x):
                return x.decode(errors="replace") if isinstance(x, bytes) else (x or "")
            return ExecResult(_s(e.stdout), _s(e.stderr) + f"\n[timeout after {timeout_s}s]", 124,
                              time.monotonic() - t0, kill={"reason": "time_limit", "category": "agent", "basis": "stand-in timeout"})

    def collect(self, dest_dir: str | Path) -> None:
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        src = self.workdir / "output"
        if src.exists():           # same layout as the real sandbox: dest/output/{report.json,mhw_mask.nc}
            shutil.copytree(src, dest / "output", dirs_exist_ok=True)

    def metadata(self) -> dict[str, Any]:
        return {"stand_in": True, "sandbox": "LocalSubprocessStandIn", "workdir": str(self.workdir)}

    def stop(self) -> None:
        self.stopped = True
        shutil.rmtree(self.workdir, ignore_errors=True)
