"""Protocol-dependent settings of the instruments.

From `protocol/report-spec.md` (origin/protocol-draft at 2aaa857), section
"Validity" item 2: the scientific output is the variable `mhw`, dimensions
(time, lat, lon), of `output/mhw_mask.nc`. Only that variable can certify
coverage; auxiliary copies or diagnostics written elsewhere cannot. A run
whose mask lacks it is not finished, so no other variable is ever guessed.

The protocol has no machine-readable outputs file, so the value is fixed
here and cited; `SPEC_SOURCE` is recorded in every audit bundle.
"""
from __future__ import annotations

SPEC_SOURCE = "protocol/report-spec.md@2aaa857"

# The scientific sink: {output file: [variables]}.
SINKS = {"mhw_mask.nc": ["mhw"]}

# Disclosure is mechanical (report-spec, "Disclosure"): a run is disclosed iff
# `complete == false` in a valid report; caveats are never parsed for it.
REPORT_FILE = "report.json"


# The words of option D's refusal of an in-place read (icsa.sandbox.gatepolicy.D_MESSAGE and
# sandbox/hooks/icsa_option_shims.py, which a test keeps in step with this): the agent's own
# request, refused by policy, carrying no errno. The tracer cannot import the gate's module.
D_REFUSAL_TEXT = "files cannot be read remotely in place"


def sink_spec() -> dict[str, list[str]]:
    return {k: list(v) for k, v in SINKS.items()}


# Inputs that are still stand-ins for another lane's work; recorded in every audit
# bundle. None left: the sink and the disclosure rule come from the protocol (above),
# the required extent from icsa.instances (#5).
PLACEHOLDERS: list[str] = []


def using_placeholders() -> list[str]:
    return list(PLACEHOLDERS)
