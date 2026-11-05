"""site_a slot equality (#34): before a slot takes its first run, compare it with the model's other slots.

Every site_a slot of a model must serve the same checkpoint with the same serving settings, or the runs spread over slots are not
comparable. Fields compared, and where each comes from:
  - `model_id`, `root`, `max_model_len`: read-only `GET <base_url>/models` (vLLM). Permission ids and `created` are ignored.
  - `checkpoint_revision` (the snapshot vLLM loaded) and `fingerprint` (`system_fingerprint` of a 1-token probe): published by the HPC
    agent per slot in endpoints.json (`identity_checked_utc` says when). They are used when present. Where the `fingerprint` key is
    ABSENT the gate sends its own probe (one chat completion, max_tokens 1, temperature 0, a one-word prompt) and records the source.
    There is no fallback for `checkpoint_revision`: without it the checkpoint cannot be verified, and that is alarmed.
  - A `null` fingerprint with `identity_checked_utc` set, for a model in `no_fingerprint_models` (Coder: vLLM 0.15.0 sends none), means
    "not provided by this server": alarm-free, distinct from a failed read, equal only to another "not provided".

Verdict per slot: "equal" (every field read on both sides and equal), "different" (some field read on both sides and not equal), or
"unknown" (no field differs but one could not be read). "different" takes the slot out of dispatch; "unknown" alarms and blocks only
when `unknown_blocks` is set. After a run, `note_run` compares the fingerprint the run recorded with the slot's own: a change alarms.

The reference of a slot is the model's other slots that are already admitted; slots that ran before this process are evaluated first. The first
slot of a model has nothing to be compared with and becomes the baseline: say so in the state, never call it "equal".

Every slot, the first included, is also held to the model's registered pin (`pins_from_models`, from config/models.toml): it must serve the pinned
api id and the pinned checkpoint revision, or it is "different", and a field that cannot be read is "unknown" (the lead, 2 Nov: a forward left
listening after its slot went down reached another model's head node). A run whose fingerprint differs from its slot's blocks that slot until its
job changes, and the scheduler retries the run as infrastructure.

Amendment 41 ("every deployment of a model serves it"): with `peer_blocks` False only that pin check, 24(f)'s identity gate (served model id and, on
site_a, the checkpoint revision), admits or excludes a slot. The peer comparison above is still made and still alarms ("different" / "unknown" stay
in the status and in `alarms_from_state`), but it never takes a slot out of dispatch, and neither does a run's fingerprint change (`note_run` records
and alarms; the run stays a run). A slot whose served id or revision cannot be read is not shown to pass the pin: it is blocked while `unknown_blocks`.
An admitted slot (not blocked) is a reference for the slots judged after it, as before, whether or not it differs from its own peers. Default True: as before.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Callable

FIELDS = ("model_id", "root", "max_model_len", "checkpoint_revision", "fingerprint")
NOT_PROVIDED = "<not provided by this server>"   # a fingerprint a server never sends (Coder); not a failed read
PROBE_PROMPT = "Hello"


@dataclass(frozen=True)
class Obs:
    """What was read from one slot; None = could not be read."""
    slot: str
    model: str
    job: str | None = None
    model_id: str | None = None
    root: str | None = None
    max_model_len: int | None = None
    fingerprint: str | None = None
    error: str | None = None
    checkpoint_revision: str | None = None
    fingerprint_source: str | None = None        # endpoints.json | probe | not_provided | None (unread)
    identity_utc: str | None = None              # when the identity was read (endpoints.json's, or the probe's)


def parse_models(body: Any, api_id: str | None) -> dict[str, Any]:
    """The served model's fields from a /v1/models body: the entry whose id is `api_id` (else the only entry). Anything else
    (several entries and none is api_id, a non-integer length) leaves the fields None."""
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, list):
        return {}
    ents = [e for e in data if isinstance(e, dict)]
    pick = [e for e in ents if api_id is not None and e.get("id") == api_id] or (ents if len(ents) == 1 else [])
    if len(pick) != 1:
        return {}
    e = pick[0]
    mml = e.get("max_model_len")
    return {"model_id": e.get("id") if isinstance(e.get("id"), str) else None,
            "root": e.get("root") if isinstance(e.get("root"), str) else None,
            "max_model_len": mml if isinstance(mml, int) and not isinstance(mml, bool) else None}


def _utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _text(v: Any) -> str | None:
    return v.strip() if isinstance(v, str) and v.strip() else None


def published_identity(entry: dict[str, Any], no_fp_models: frozenset[str] | set[str] = frozenset()) -> dict[str, Any]:
    """checkpoint_revision, fingerprint, fingerprint_source and identity_utc as endpoints.json publishes them; `fingerprint_source`
    is None when the `fingerprint` key is absent (the caller may then probe) or the value is unreadable."""
    out: dict[str, Any] = {"checkpoint_revision": _text(entry.get("checkpoint_revision")), "fingerprint": None,
                           "fingerprint_source": None, "identity_utc": _text(entry.get("identity_checked_utc"))}
    if "fingerprint" in entry:
        fp = _text(entry["fingerprint"])
        if fp:
            out.update(fingerprint=fp, fingerprint_source="endpoints.json")
        elif entry["fingerprint"] is None and out["identity_utc"] and str(entry.get("model")) in no_fp_models:
            out.update(fingerprint=NOT_PROVIDED, fingerprint_source="not_provided")
    return out


def _post_probe(base: str, api_id: str | None, timeout: float, opener: Callable[..., Any]) -> str | None:
    """One chat completion, max_tokens 1, temperature 0: the `system_fingerprint` of the response, or None."""
    body = json.dumps({"model": api_id, "messages": [{"role": "user", "content": PROBE_PROMPT}], "max_tokens": 1,
                       "temperature": 0}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body, headers={"Content-Type": "application/json"})
    with opener(req, timeout=timeout) as r:
        resp = json.loads(r.read().decode())
    return _text(resp.get("system_fingerprint")) if isinstance(resp, dict) else None


def http_probe(entry: dict[str, Any], timeout: float = 10.0, opener: Callable[..., Any] = urllib.request.urlopen,
               no_fp_models: frozenset[str] | set[str] = frozenset()) -> Obs:
    """Read one slot: GET <base_url>/models (read-only), the identity endpoints.json publishes, and, only where the `fingerprint` key is
    absent, the 1-token probe. A slot with no base_url, or one that does not answer, is all-unknown."""
    slot, model, job = str(entry.get("slot")), str(entry.get("model")), entry.get("backend_job")
    ident = published_identity(entry, no_fp_models)
    base = entry.get("base_url")
    if not base:
        return Obs(slot, model, job, error="no base_url", **ident)
    try:
        with opener(str(base).rstrip("/") + "/models", timeout=timeout) as r:
            body = json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001 - an unreachable or garbled slot is "unknown", never a guess
        return Obs(slot, model, job, error=f"{type(e).__name__}: {e}"[:200], **ident)
    got = parse_models(body, entry.get("api_id"))
    err = None if got else "unreadable /models body"
    if "fingerprint" not in entry and got:
        try:
            fp = _post_probe(str(base), entry.get("api_id"), timeout, opener)
        except Exception as e:  # noqa: BLE001
            fp, err = None, f"fingerprint probe failed: {type(e).__name__}: {e}"[:200]
        if fp:
            ident.update(fingerprint=fp, fingerprint_source="probe", identity_utc=_utcnow())
        elif err is None and model in no_fp_models:
            ident.update(fingerprint=NOT_PROVIDED, fingerprint_source="not_provided", identity_utc=_utcnow())
    return Obs(slot, model, job, error=err, **ident, **got)


_UNSET: Any = object()      # note_run: no expectation given (use the slot's current fingerprint), as against None = unknown at the start


REV_IN_NOTE = re.compile(r"\brev ([0-9a-f]{7,40})\b")


def pins_from_models(models: dict[str, Any]) -> dict[str, dict[str, str | None]]:
    """endpoints.json model name -> {"api_id", "revision"}: what each site_a model must serve. The revision is the "rev <hex>" of the model's frozen
    hpc note; a note without one leaves it None, which no slot can match, so the slot is unknown, never passed."""
    out = {}
    for spec in models.values():
        if getattr(spec, "kind", None) != "openai_compat":
            continue
        note = (getattr(spec, "version_notes", None) or {}).get("hpc") or getattr(spec, "version_note", "") or ""
        m = REV_IN_NOTE.search(note)
        out[spec.endpoint_name] = {"api_id": spec.api_id, "revision": m.group(1) if m else None}
    return out


def pin_check(obs: Obs, pin: dict[str, Any] | None) -> tuple[str, list[str]] | None:
    """("different" | "unknown", reasons) when a slot is not shown to serve its model's pin; None when it is."""
    if pin is None:
        return "unknown", [f"no registered pin for model {obs.model}"]
    diff, unk = [], []
    if obs.model_id is None:
        unk.append("served model id unread")
    elif obs.model_id != pin.get("api_id"):
        diff.append(f"serves {obs.model_id!r}, pinned {pin.get('api_id')!r}")
    if not pin.get("revision"):
        unk.append(f"the pin of {obs.model} has no revision")
    elif obs.checkpoint_revision is None:
        unk.append("checkpoint_revision unread")
    elif not obs.checkpoint_revision.lower().startswith(str(pin["revision"]).lower()):
        diff.append(f"checkpoint_revision {obs.checkpoint_revision!r}, pinned {pin['revision']!r}")
    if diff:
        return "different", diff
    return ("unknown", unk) if unk else None


def compare(cand: Obs, ref: Obs) -> dict[str, str]:
    """Per field: equal, different, or unknown (not read on one side or both)."""
    out = {}
    for f in FIELDS:
        a, b = getattr(cand, f), getattr(ref, f)
        if a is None or b is None or (f == "fingerprint" and a != b and NOT_PROVIDED in (a, b)):
            out[f] = "unknown"         # one side unread, or a server that sends no fingerprint set against one that does
        else:
            out[f] = "equal" if a == b else "different"
    return out


def verdict(cand: Obs, refs: list[Obs]) -> tuple[str, list[str]]:
    """("equal" | "different" | "unknown" | "baseline", reasons) of a candidate against the references."""
    if not refs:
        unread = [f for f in FIELDS if getattr(cand, f) is None and not (f == "fingerprint" and cand.error is None)]
        if cand.error is not None or any(getattr(cand, f) is None for f in ("model_id", "root", "max_model_len")):
            # the first slot is the reference the others are held to: if its serving fields cannot be read it is unknown, not a baseline
            return "unknown", [f"first slot of the model, its serving fields could not be read ({cand.error or ', '.join(unread)})"]
        return "baseline", ["first slot of the model: nothing to compare with"]
    diff, unk = [], []
    for ref in refs:
        for f, v in compare(cand, ref).items():
            if v == "different":
                diff.append(f"{f} {getattr(cand, f)!r} differs from {getattr(ref, f)!r} ({ref.slot})")
            elif v == "unknown":
                unk.append(f"{f} unreadable on {cand.slot if getattr(cand, f) is None else ref.slot}")
    if diff:
        return "different", diff
    if unk:
        return "unknown", sorted(set(unk))
    return "equal", []


class SlotGate:
    """Checks every up slot before it takes a run. `probe(entry) -> Obs` is injectable (tests, no network).

    A slot is probed once per state of its endpoints.json entry (`_key`: job, fingerprint, address, model, api id). When any slot of a
    model changed, the whole model group is judged again from the current observations, so a reference that was replaced never keeps a
    verdict alive. Order: unchanged admitted slots first (they stay the references), then slots that ran before, then by name; the first is the baseline."""

    def __init__(self, probe: Callable[[dict[str, Any]], Obs] | None = None, unknown_blocks: bool = False,
                 retry_s: float = 60.0, clock: Callable[[], float] = time.monotonic,
                 no_fingerprint_models: frozenset[str] | set[str] = frozenset({"qwencoder"}), pins: dict[str, dict] | None = None,
                 peer_blocks: bool = True):
        self.pins = pins       # None: peers only (unit tests of the peer rule); the campaign always passes the registered pins
        self.peer_blocks = peer_blocks   # False (amendment 41): the pin check alone blocks; the peer comparison and a run's fingerprint change only alarm
        self.no_fingerprint_models = frozenset(no_fingerprint_models)
        self.probe = probe or (lambda e: http_probe(e, no_fp_models=self.no_fingerprint_models))
        self.unknown_blocks, self.retry_s, self._clock = unknown_blocks, retry_s, clock
        self._retry_at: dict[str, float] = {}         # slot -> when a failed probe may be repeated
        self._restored: set[str] = set()              # slots whose verdict came from a previous process (see restore)
        self._seen: dict[str, tuple] = {}             # slot -> the entry fields last probed (see _key)
        self._obs: dict[str, Obs] = {}                # slot -> its last observation
        self._up: dict[str, frozenset[str]] = {}      # model -> the slots that were up at the last evaluation
        self.status: dict[str, dict[str, Any]] = {}   # slot -> {"verdict", "reasons", "blocked", "model", "job", ...}

    def restore(self, state: dict[str, Any] | None) -> None:
        """Take the verdicts a previous process recorded (state()), so a restart does not forget which slot was the reference and
        which was blocked. They only order the first evaluation: every slot is probed again, and a restored slot whose job changed
        is judged as new."""
        for slot, st in ((state or {}).get("slots") or {}).items():
            if isinstance(st, dict) and "blocked" in st and "job" in st:
                self.status[slot] = dict(st)
                self._restored.add(slot)

    @staticmethod
    def _key(e: dict[str, Any]) -> tuple:
        return (e.get("backend_job"), e.get("fingerprint"), e.get("checkpoint_revision"), e.get("identity_checked_utc"),
                e.get("base_url"), e.get("model"), e.get("api_id"), "fingerprint" in e)

    def update(self, entries: list[dict[str, Any]] | None, ran: set[str] | frozenset[str] = frozenset()) -> bool:
        """Probe the up slots whose entry changed, then re-judge their models. `ran`: slots that took runs before this process; they
        are the references, but one that differs is blocked all the same (a restarted job of a used slot may serve something else).
        Returns True when the status changed."""
        if entries is None:
            return False                               # unreadable endpoints file: keep the state
        up = [e for e in entries if e.get("up") and e.get("slot") is not None]
        up_names = {str(e["slot"]) for e in up}
        for gone in [k for k in self._seen if k not in up_names]:
            del self._seen[gone]                       # a slot that is down may serve something else when it returns: probe it again
            self._obs.pop(gone, None)
        touched: set[str] = set()
        fresh: set[str] = set()                        # slots probed in this call
        for e in up:
            slot = str(e["slot"])
            retry = (slot in self._obs and self._obs[slot].error is not None and self._clock() >= self._retry_at.get(slot, 0.0))
            if self._seen.get(slot) != self._key(e) or retry:
                new_obs = self.probe(e)
                if new_obs.error is not None:          # unreadable serving fields: try again after retry_s, whatever the entry says
                    self._retry_at[slot] = self._clock() + self.retry_s
                if retry and new_obs == self._obs[slot]:
                    continue                           # still unreadable in the same way: nothing to judge again
                prev = self._obs.get(slot)
                # a re-read that shows the same identity (only the entry's timestamp moved) is not a new slot: it keeps its place
                same = (prev is not None and prev.error is None and new_obs.error is None
                        and tuple(getattr(prev, f) for f in FIELDS) == tuple(getattr(new_obs, f) for f in FIELDS)
                        and (self.status.get(slot) or {}).get("job") == e.get("backend_job"))
                self._obs[slot] = new_obs
                self._seen[slot] = self._key(e)
                touched.add(str(e.get("model")))
                if not same:
                    fresh.add(slot)
        now_up: dict[str, set[str]] = {}
        for e in up:
            now_up.setdefault(str(e.get("model")), set()).add(str(e["slot"]))
        for model in set(now_up) | set(self._up):
            was, is_ = self._up.get(model, frozenset()), frozenset(now_up.get(model, ()))
            if was != is_:                             # a slot appeared, returned or went down: its model is judged again
                touched.add(model)
                fresh |= set(is_) - set(was)           # a returning slot is not "continuously admitted": it is compared like a new one
            self._up[model] = is_
        changed = False
        for model in sorted(touched):
            # References first: an unchanged slot that was admitted keeps being one, so a restarted slot is compared with the peers
            # that did not change, never installed as the baseline over them. Then slots that ran before, then by name.
            def order(e):
                slot = str(e["slot"])
                st = self.status.get(slot)
                keeps = (st is not None and not st["blocked"] and st.get("job") == e.get("backend_job")
                         and (slot not in fresh or slot in self._restored))
                return (not keeps, slot not in ran, slot)
            group = sorted((e for e in up if str(e.get("model")) == model), key=order)
            admitted: list[Obs] = []
            for e in group:
                slot, obs = str(e["slot"]), self._obs[str(e["slot"])]
                v, why = verdict(obs, admitted)
                # with the peer rule off there is no pin table only by a caller's choice: a model with no pin is then "unknown" (not shown to pass 24(f)), never admitted by silence
                pc = pin_check(obs, (self.pins or {}).get(model)) if (self.pins is not None or not self.peer_blocks) else None
                if pc is not None:
                    v, why = (pc[0] if pc[0] == "different" or v in ("baseline", "equal") else v), why + pc[1]
                prev = self.status.get(slot) or {}
                run_blocked = prev.get("run_blocked") if prev.get("job") == e.get("backend_job") else None   # ends only with the job
                if self.peer_blocks:
                    blocked = v == "different" or (v == "unknown" and self.unknown_blocks) or bool(run_blocked)
                else:       # amendment 41: 24(f)'s pin check alone; a run_blocked a process with the peer rule on recorded does not hold the slot
                    run_blocked = None
                    blocked = pc is not None and (pc[0] == "different" or (pc[0] == "unknown" and self.unknown_blocks))
                if not blocked:
                    admitted.append(obs)
                new = {"verdict": v, "reasons": why, "blocked": blocked, "model": obs.model, "job": e.get("backend_job"), "run_blocked": run_blocked,
                       "observed": {f: getattr(obs, f) for f in FIELDS}, "probe_error": obs.error,
                       "fingerprint_source": obs.fingerprint_source, "identity_utc": obs.identity_utc,
                       "run_mismatches": (self.status.get(slot) or {}).get("run_mismatches", []) if (self.status.get(slot) or {}).get("job") == e.get("backend_job") else []}
                if not self.peer_blocks:       # why a "different" slot may not be blocked: the peer rule is off, and this is the pin's outcome (the default's status is unchanged)
                    new.update(peer_blocks=False, pin="pass" if pc is None else pc[0])
                if self.status.get(slot) != new:
                    self.status[slot], changed = new, True
        self._restored.clear()
        return changed

    def allowed(self, slot: str) -> bool:
        """False for a slot taken out of dispatch, and for a slot the gate has no verdict on at all: a slot is never admitted by the gate's silence (a status that is
        missing is not "not blocked"). Callers call update() first, so every up slot has been evaluated."""
        s = self.status.get(slot)
        return s is not None and not s["blocked"]

    def identity(self, slot: str) -> dict[str, Any] | None:
        """What the gate knows of a slot's identity (for the run record), or None for a slot it has not judged."""
        st = self.status.get(slot)
        if not st:
            return None
        o = st["observed"]
        return {"checkpoint_revision": o.get("checkpoint_revision"), "fingerprint": o.get("fingerprint"),
                "fingerprint_source": st.get("fingerprint_source"), "identity_utc": st.get("identity_utc"),
                "verdict": st["verdict"], "root": o.get("root"), "max_model_len": o.get("max_model_len")}

    def note_run(self, slot: str, run_key: str, fingerprints: list[str], expected: Any = _UNSET) -> str | None:
        """After a run: the system fingerprints the run recorded against the slot's own. A different one means the slot changed
        under the run (restarted with other weights): recorded in the slot's status, returned as the alarm text, and the slot is blocked unless `peer_blocks`
        is False. A slot whose
        fingerprint is unknown or not provided cannot be checked; nothing is said then."""
        st = self.status.get(slot)
        if not st:
            return None
        # the identity when the attempt started; None there means it was unknown then (nothing to check), never "use today's"
        want = st["observed"].get("fingerprint") if expected is _UNSET else expected
        if not want or want == NOT_PROVIDED:
            return None
        bad = sorted({f for f in fingerprints if f != want})
        if not bad:
            return None
        msg = f"run {run_key} on {slot} recorded system_fingerprint {', '.join(bad)} but the slot was checked as {want}"
        ms = st.setdefault("run_mismatches", [])
        if msg not in ms and len(ms) < 20:
            ms.append(msg)
        if self.peer_blocks:
            st["blocked"], st["run_blocked"] = True, msg      # out of dispatch until its job changes (the lead, 2 Nov)
        return msg                                            # amendment 41 (peer_blocks False): recorded and alarmed, the slot stays as the pin check left it

    def state(self) -> dict[str, Any]:
        out: dict[str, Any] = {"unknown_blocks": self.unknown_blocks, "slots": {k: dict(v) for k, v in sorted(self.status.items())}}
        if not self.peer_blocks:
            out["peer_blocks"] = False
        return out


def run_fingerprints(model_version: str | None) -> list[str]:
    """The system fingerprints in a run record's `model_version` ("...; system_fingerprint: a, b")."""
    m = re.search(r"system_fingerprint:\s*([^;]*)", model_version or "")
    return [x.strip() for x in m.group(1).split(",") if x.strip()] if m else []


def alarms_from_state(state: dict[str, Any] | None) -> list[str]:
    """Alarm lines for progress: every slot out of dispatch, every slot whose equality could not be shown, every identity that cannot
    be read (so the checkpoint cannot be verified), and every run whose fingerprint differs from its slot's."""
    if not state:
        return []
    out = []
    for slot, s in sorted(state.get("slots", {}).items()):
        if s["verdict"] == "different":
            where = "is OUT OF DISPATCH" if s["blocked"] else "stays in dispatch (it passes the registered pin; the peer comparison alarms only, amendment 41)"
            out.append(f"SLOT {slot} ({s['model']}) differs from the model's other slots and {where}: " + "; ".join(s["reasons"]))
        elif s["verdict"] == "unknown":
            out.append(f"SLOT {slot} ({s['model']}) equality with the model's other slots is UNKNOWN"
                       f"{' and it is OUT OF DISPATCH' if s['blocked'] else ''}: " + "; ".join(s["reasons"]))
        o = s.get("observed", {})
        gaps = [f for f in ("checkpoint_revision", "fingerprint") if o.get(f) is None]
        if gaps and s["verdict"] != "unknown":
            out.append(f"SLOT {slot} ({s['model']}): {' and '.join(gaps)} not read, so the checkpoint cannot be verified for this slot")
        for m in s.get("run_mismatches", []):
            out.append(f"SLOT {slot} ({s['model']}) CHANGED UNDER A RUN: {m}")
    return out
