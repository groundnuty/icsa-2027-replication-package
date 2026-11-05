"""The instruments directory for the sandbox's instrumentation slot (#7).

#7's `sitecustomize` imports `$ICSA_INSTRUMENT_MODULE` at every interpreter
start, from a directory mounted read-only at /opt/icsa/instruments and put
first on PYTHONPATH:

    d, module = build_instruments_dir(run_scratch / "instruments")
    SandboxConfig(instruments_dir=d, instrument_module=module, ...)

The directory holds only the in-process tracer (hooks, tracer, prov, config;
pure Python over numpy) and a boot module that installs it. The offline
analysis never runs in the sandbox.

Environment the tracer reads (the boot module sets the defaults):
- `ICSA_TRACE_DIR`: where the tracer writes its streams (default `/trace`,
  which #7 copies out);
- `ICSA_OUTPUT_DIR`: the run's output directory, the only place a sink write
  can certify coverage (default `$ICSA_WORK_DIR/output`, `ICSA_WORK_DIR`
  defaulting to `/work`, the agent's working directory in #7). If the agent
  writes `output/` anywhere else, nothing certifies and the run is unknown.
"""
from __future__ import annotations

import shutil
from pathlib import Path

IN_SANDBOX = ("__init__.py", "hooks.py", "tracer.py", "prov.py", "config.py")
BOOT_MODULE = "icsa_omission_instrument"

BOOT_SOURCE = '''"""Boot module for #9's tracer, imported by the sandbox's sitecustomize."""
import os

os.environ.setdefault("ICSA_TRACE_DIR", "/trace")
os.environ.setdefault("ICSA_OUTPUT_DIR",
                      os.path.join(os.environ.get("ICSA_WORK_DIR", "/work"), "output"))

from icsa.instruments import hooks as _hooks  # noqa: E402

_hooks.install_from_env()
'''


def build_instruments_dir(dest) -> tuple[Path, str]:
    """Write the instruments directory at `dest` (replaced if present); return it and
    the module name to set as ICSA_INSTRUMENT_MODULE."""
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    pkg = dest / "icsa" / "instruments"
    pkg.mkdir(parents=True)
    src = Path(__file__).resolve().parent
    (dest / "icsa" / "__init__.py").write_text('"""Tracer-only copy of icsa for the sandbox (#9)."""\n')
    for name in IN_SANDBOX:
        shutil.copy2(src / name, pkg / name)
    (dest / f"{BOOT_MODULE}.py").write_text(BOOT_SOURCE)
    return dest, BOOT_MODULE
