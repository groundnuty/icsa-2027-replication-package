"""Instrumentation slot: runs at every Python interpreter start in the sandbox.

Imports the module named by ICSA_INSTRUMENT_MODULE (default: the no-op module
`icsa_noop_instrument`). The module is looked up on PYTHONPATH; the #9 lane
supplies its own by mounting a directory at /opt/icsa/instruments (the sandbox
puts it first on PYTHONPATH) and setting the variable. It may write under
ICSA_TRACE_DIR, which `Sandbox.collect` copies out.

A failing instrument must never break the agent's code, but the failure is
not silent: it is appended to $ICSA_TRACE_DIR/instrument-error.log.
"""
import importlib
import os
import traceback

if os.environ.get("ICSA_OPTION") in ("T", "T-unpaginated", "D"):
    try:
        import icsa_option_shims  # noqa: F401
    except Exception:  # noqa: BLE001
        pass  # the gate still enforces; only the friendly messages are lost

_name = os.environ.get("ICSA_INSTRUMENT_MODULE", "")
if _name:
    try:
        importlib.import_module(_name)
    except Exception:  # noqa: BLE001
        try:
            d = os.environ.get("ICSA_TRACE_DIR", "/trace")
            with open(os.path.join(d, "instrument-error.log"), "a") as f:
                f.write(traceback.format_exc() + "\n")
        except OSError:
            pass
