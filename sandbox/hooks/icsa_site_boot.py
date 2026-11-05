"""Loads the instrument in every Python of a traced sandbox, whatever its environment (science, #2, 2 Nov 05:44Z).

A `.pth` line in the interpreter's site-packages imports this module, so it runs for `python -I` and `python -E` and for a child
started with a scrubbed environment, none of which see PYTHONPATH. (`python -S` skips site altogether: it leaves no start record, so
its launch stays unmatched and the run is `unknown`.) A sandbox is traced when the instruments directory is mounted; otherwise this
does nothing. The order stays sitecustomize's: the option's shims, then the instrument.
"""
import os
import sys

_HOOKS, _INSTRUMENTS, _BOOT = "/opt/icsa/hooks", "/opt/icsa/instruments", "icsa_omission_instrument"


def _boot():
    if not os.path.isfile(os.path.join(_INSTRUMENTS, _BOOT + ".py")):
        return
    for p in (_HOOKS, _INSTRUMENTS):
        if p not in sys.path:
            sys.path.insert(0, p)
    os.environ.setdefault("ICSA_INSTRUMENT_MODULE", _BOOT)
    os.environ.setdefault("ICSA_TRACE_DIR", "/trace")
    import sitecustomize  # noqa: F401  (idempotent: site imports it again, cached)


try:
    _boot()
except Exception:  # noqa: BLE001 - never into the agent's code; no start record is left, so the run is not read as clean
    pass
