"""Builds the Python source one scripted run executes in the sandbox: the spec, #4's source, the script.

`refdet` is shipped as a tar (base64, in the code itself) and unpacked to the sandbox's /tmp, so /work stays what a
run wrote. `Sandbox` is unchanged: this is an ordinary `exec` of Python source. The tar's sha256 is recorded per run.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]     # .../icsa
SOURCES = ["__init__.py", "grid.py", "extent.py", "paths.py", "ncio.py", "refdet/__init__.py", "refdet/core.py",
           "refdet/data.py", "refdet/fieldcache.py", "refdet/truth.py"]     # a test imports refdet from these alone
PACKAGE_DIR = "/tmp/icsa_pkg"


def source_tar() -> bytes:
    """A reproducible tar of the #4 sources (fixed names, modes and times, sorted)."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tf:
        for rel in sorted(SOURCES):
            data = (ROOT / rel).read_bytes()
            info = tarfile.TarInfo(f"icsa/{rel}")
            info.size = len(data)
            info.mode = 0o644
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def source_sha256() -> str:
    return hashlib.sha256(source_tar()).hexdigest()


def script_source() -> str:
    return (Path(__file__).parent / "insandbox.py").read_text()


def import_smoke_code() -> str:
    """The script's import stage alone, for a sandbox with the tracer in its slot: no data, no network. Exit 0 proves nothing by itself, so it also says
    where the modules came from, and whether the tracer was really loaded."""
    payload = base64.b64encode(source_tar()).decode()
    return (f"{script_source()}\nimport base64 as _b, io as _i, tarfile as _t, json as _j, sys as _s\n"
            f"_t.open(fileobj=_i.BytesIO(_b.b64decode('{payload}'))).extractall({PACKAGE_DIR!r}, filter='data')\n"
            f"_use_package({PACKAGE_DIR!r})\nfrom icsa import refdet\nfrom icsa.extent import CellBox\n"
            "import os as _o\n_h = _s.modules.get('icsa.instruments.hooks')\n"
            "_e = _o.path.join(_o.environ.get('ICSA_TRACE_DIR', '/trace'), 'instrument-error.log')\n"
            "_err = open(_e).read()[-300:] if _o.path.exists(_e) else None\n"
            f"print(_j.dumps({{'refdet': refdet.__file__, 'tracer_hooks': getattr(_h, '__file__', None), 'tracer_error': _err, 'package_dir': {PACKAGE_DIR!r}}}))\n")


def pipeline_code(spec: dict, *, before: str = "", after: str = "") -> str:
    """Source for `Sandbox.exec`: unpack #4, set SPEC, run the script's main. `before` and `after` wrap the main call, and
    follow the script's source: nothing may precede its `from __future__` line."""
    payload = base64.b64encode(source_tar()).decode()
    unpack = (
        "import base64 as _b, io as _i, tarfile as _t\n"
        f"_t.open(fileobj=_i.BytesIO(_b.b64decode('{payload}'))).extractall({PACKAGE_DIR!r}, filter='data')\n"
    )
    spec = {**spec, "package_dir": PACKAGE_DIR}
    # __future__ must open the module, so the script's own source goes first and the driver last
    return f"{script_source()}\n{unpack}{before}SPEC = {json.dumps(spec)!r}\nmain(json.loads(SPEC))\n{after}"


def spec_for(rec: dict, option: str, layout: str, base_days, target_days, *, trace_http: bool = False,
             workdir: str = "/work", location: str | None = None, read_days=None) -> dict:
    """The script's input, from a #5 manifest record and the required days derived by `icsa.instances.load`. `read_days` (a live probe's prefix of the cell's
    days): the key is in the spec only when it is given, so every other run's spec is what it was."""
    i = rec["instance"]
    spec = {"instance_id": i["instance_id"], "option": option, "layout": layout,
            "lat0": i["lat0"], "lat1": i["lat1"], "lon0": i["lon0"], "lon1": i["lon1"],
            "lat_min": i["lat_min"], "lat_max": i["lat_max"], "lon_min": i["lon_min"], "lon_max": i["lon_max"],
            "base_days": [int(x) for x in base_days], "target_days": [int(x) for x in target_days],
            "trace_http": trace_http, "workdir": workdir, "location": location}
    if read_days is not None:
        spec["read_days"] = [int(x) for x in read_days]
    return spec
