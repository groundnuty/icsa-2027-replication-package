"""The slot-user token source for the baselines (science, #2, 18:17Z; the call is lane-slots', `feat/8-slot-tokens`).

`ICSA_TOKEN_SOURCE=icsa.scripted.slot_tokens:factory`. Each run waits for a free slot user of ITS option, holds it for the whole
run and mints its one token as that user: REST for T, T-unpaginated and D, oneclient for M (the sidecar's too). The lease is
released on every exit. There is no fallback to admin: an option with no slot (M+) fails the run, so M+ and the WAN anchor stay
on their own processes with the admin source. The token's value is never printed or recorded; the run's record gets the slot's
interval (`onedata_slot`) and the token's fingerprint record.
"""
from __future__ import annotations

import contextlib
from typing import Callable

from ..records import Option

INTERFACE = {Option.T: "rest", Option.T_UNPAGINATED: "rest", Option.D: "rest", Option.M: "oneclient"}


class _SlotLease:
    def __init__(self, lt, interface: str):
        self._lt, self._interface = lt, interface
        self.slot, self.subject = lt.lease.slot, lt.lease.user_id

    def mint(self, mint_admin, interface, ttl_s, caveats) -> str:
        if interface != self._interface:
            raise RuntimeError(f"the slot token is a {self._interface} token; a {interface} token was asked for")
        return self._lt.token

    def final_record(self) -> dict:
        """After the release: {slot, user_id, start, end, wait_s} plus the token's fingerprint record."""
        return {**self._lt.lease.record(), "wait_s": self._lt.lease.wait_s, "token_record": self._lt.record.as_dict()}


class SlotTokens:
    kind = "slot"

    def __init__(self, leased_token: Callable | None = None, time_cap_s: float | None = None, timeout_s: float | None = None):
        if time_cap_s is None:
            from .federation import RUN_TIME_CAP_S as time_cap_s
        self._leased, self._cap, self._timeout = leased_token, float(time_cap_s), timeout_s

    @contextlib.contextmanager
    def lease(self, run_key: str, option: str):
        opt = Option(option)
        if opt not in INTERFACE:
            raise RuntimeError(f"no slot users for {opt.value}: it stays on its own path, never on admin")
        leased = self._leased
        if leased is None:
            from ..harness.real_sandbox import leased_token as leased       # lane-slots' call; absent until that branch lands
        with leased(opt.value, self._cap, run_key=run_key, timeout_s=self._timeout) as lt:
            yield _SlotLease(lt, INTERFACE[opt])


def factory() -> SlotTokens:
    return SlotTokens()
