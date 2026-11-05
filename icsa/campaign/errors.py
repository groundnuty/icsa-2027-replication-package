"""The infra-failure signal of the #8 contract."""
from __future__ import annotations

KINDS = ("endpoint", "sandbox", "onedata_health", "key_rejected")
KEY_REJECTED = "key_rejected"                  # the model API refused the key (HTTP 401 or 403): the unit is held, no attempt is charged (scheduler._hold_key)
ONEDATA_OUTAGE = "onedata_outage"            # an attempt's infra_kind when its post-run health check failed while the health gate was closed, or in flight as it closed: kept (tokens and all) as a discarded attempt, charged to no run (healthgate.py)
PRE_CHECK_FAILED = "pre-run check failed"     # an attempt's infra_detail begins so when no sandbox started and no executor ran (the scheduler; the status counts them)


class InfraError(Exception):
    """A failure outside the agent's control: a model endpoint error that
    persisted after the transport retries, or a sandbox crash not caused by
    agent code. Never for slowness, agent-code exceptions or caps."""

    def __init__(self, kind: str, detail: str = ""):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


def is_infra_error(e: BaseException) -> bool:
    # Duck-typed so an InfraError defined in the #8 package also counts.
    return isinstance(e, InfraError) or (
        type(e).__name__ == "InfraError" and hasattr(e, "kind") and hasattr(e, "detail"))
