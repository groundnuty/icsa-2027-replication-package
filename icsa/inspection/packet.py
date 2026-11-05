"""Blind packets for code inspection (rubric §3), built from a run directory.

A packet is ONE text: the task prompt as the agent saw it, the code cells in order with numbered
lines and each cell's exit code, stdout and stderr (each kept whole up to 2,000 characters,
otherwise its first and last 1,000 characters), and the files the run wrote with their final
sizes. Nothing else: no final report or self-assessment (the agent's last message and the
content of `report.json` are not shown; its name and size are), no instrument label, bounds or
extents, no option, model or set name as metadata, no other run. The packet id is not in the
text either: it is a keyed hash (`packet_id`) used only as a file name, so the text depends on
the run's content alone (tests/inspection: a run under another option, model, label or set gives
a byte-identical packet).

Where the pieces come from (the harness's run directory, icsa/harness/runner.py):
- the prompt: the system message (empty for the protocol prompt) and the first user message of
  `transcript.json`;
- the cells: `code_cells.json` (what ran), paired in order with the python tool calls of the
  transcript whose result starts with `exit_code:` (the ones that ran); stdout and stderr are
  split out of that result text, which is what the agent saw (already capped by the harness).
  A python call that never ran (malformed arguments, the time cap reached) has no cell and is
  not shown. If the two lists disagree the packet is refused (PacketError), never guessed;
- the files: everything under `output/`, with sizes. Files a run wrote elsewhere in its sandbox
  are not collected by the harness and so are not listed; the code that wrote them is shown.

Sanitised, with semantics kept (rubric §3): every identifier in `identifiers` (the run key, the
instance id and other scenario names, model names, run directories) is replaced everywhere in
the text, case-insensitively, by a neutral token of its kind, consistently within the packet
(the first scenario name seen is SCENARIO_A, the next SCENARIO_B, ...). The access paragraph of
the prompt and the code itself still show the option; that cannot be hidden.

Every rendered packet is scanned for cues (`scan`). BLOCKING cues (a residual identifier, a set
name, answer-key words, an answer-key assertion such as "expected answer: complete", an instrument
label record) refuse the packet, wherever they are, the task prompt included. REVIEW cues (words such
as "omitting", "complete", "expected", "ground truth", "assert") are recorded in the key for the 10%
cue reading; agent code may legitimately say them, so they never refuse a real run. A K-test packet
(code we wrote) is built `strict`: any review cue refuses it too.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

CLIP = 2000
HALF = 1000
TOKEN_KINDS = ("RUN", "SCENARIO", "MODEL", "DIR", "ENDPOINT")
ENDPOINT = "ENDPOINT"     # one neutral token for every host, port and IP address (science, #76, 20:57Z)
# One neutral token for every printed duration in the cells' outputs, in EVERY packet, real and known-answer alike, as for
# endpoints: printed timings differ between the local simulation and the platform, so they are a tell (lane-k, 2 Nov: 16 of
# 31 known-answer packets carried the agent code's own elapsed-time prints). Only a number with a lower-case time unit is
# replaced, the whole number including any exponent ("1.234e-05 s"), so a latitude such as "30 S" stays. Colon forms are
# NOT replaced: "rows 10:20" may be a printed index range a coder needs (Codex review, 2 Nov); they stay a review cue,
# which refuses a known-answer packet.
DURATION = "DURATION"
_DURATION = re.compile(r"(?<![\w.+:-])\d+(?:\.\d+)?(?:[eE][-+]?\d+)?[ \t]?(?:s|sec|secs|seconds|ms|min|mins|minutes)\b(?![\w/])")


def sanitise_durations(text: str) -> str:
    """Printed durations (cell outputs only: code has slices such as 10:20) become DURATION."""
    return _DURATION.sub(DURATION, text) if text else text


class PacketError(ValueError):
    pass


def packet_id(secret: str, run_key: str) -> str:
    """Opaque id: HMAC-SHA256 of the run key under the queue's secret (kept in the key file)."""
    return "P" + hmac.new(secret.encode(), run_key.encode(), hashlib.sha256).hexdigest()[:12]


def clip(s: str) -> str:
    """Whole up to CLIP characters, else the first and last HALF with the gap stated."""
    if len(s) <= CLIP:
        return s
    return s[:HALF] + f"\n[... {len(s) - 2 * HALF} characters omitted ...]\n" + s[-HALF:]


@dataclass
class Cell:
    code: str
    exit_code: int | None
    note: str
    stdout: str
    stderr: str


@dataclass
class RunView:
    prompt: str
    cells: list[Cell]
    files: list[tuple[str, int]]
    warnings: list[str] = field(default_factory=list)


def _text(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return str(content)


def _python_calls(msgs: list[dict]) -> tuple[list[tuple[str, object]], dict[str, str]]:
    calls, results = [], {}
    for m in msgs:
        role, content = m.get("role"), m.get("content")
        if role == "assistant":
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function") or {}
                if fn.get("name") != "python":
                    continue
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except (json.JSONDecodeError, TypeError):
                    args = {}
                calls.append((tc.get("id"), args.get("code") if isinstance(args, dict) else None))
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "python":
                        inp = b.get("input") if isinstance(b.get("input"), dict) else {}
                        calls.append((b.get("id"), inp.get("code")))
        elif role == "tool":
            results[m.get("tool_call_id")] = _text(content)
        elif role == "user" and isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    results[b.get("tool_use_id")] = _text(b.get("content"))
    return calls, results


_EXIT = re.compile(r"^exit_code: (-?\d+)\n")
_OUT, _ERR = "--- stdout ---\n", "\n--- stderr ---\n"


def split_result(text: str) -> tuple[int | None, str, str, str]:
    """(exit code, note, stdout, stderr) of a python tool result as the harness wrote it:
    `exit_code: N\\n[note\\n]--- stdout ---\\n<out>\\n--- stderr ---\\n<err>`, possibly cut by the
    harness cap (then the stderr marker may be gone and everything after stdout's marker is stdout)."""
    m = _EXIT.match(text)
    code = int(m.group(1)) if m else None
    rest = text[m.end():] if m else text
    i = rest.find(_OUT)
    if i < 0:
        return code, rest.strip("\n"), "", ""
    note, body = rest[:i].strip("\n"), rest[i + len(_OUT):]
    j = body.rfind(_ERR)
    if j < 0:
        return code, note, body, ""
    return code, note, body[:j], body[j + len(_ERR):]


def read_run(run_dir) -> RunView:
    run_dir = Path(run_dir)
    tpath, cpath = run_dir / "transcript.json", run_dir / "code_cells.json"
    if not tpath.is_file() or not cpath.is_file():
        raise PacketError(f"{run_dir}: transcript.json or code_cells.json missing")
    t = json.loads(tpath.read_text())
    msgs = t.get("system_and_messages") if isinstance(t, dict) else t
    if not isinstance(msgs, list) or not msgs:
        raise PacketError(f"{run_dir}: empty transcript")
    system = "\n\n".join(_text(m.get("content")) for m in msgs if m.get("role") == "system").strip()
    user = next((m for m in msgs if m.get("role") == "user"), None)
    if user is None:
        raise PacketError(f"{run_dir}: no user message")
    prompt = (system + "\n\n" if system else "") + _text(user.get("content"))
    calls, results = _python_calls(msgs)
    ran = [(cid, code, results[cid]) for cid, code in calls
           if isinstance(results.get(cid), str) and _EXIT.match(results[cid])]
    cells_json = json.loads(cpath.read_text())
    if not isinstance(cells_json, list):
        raise PacketError(f"{run_dir}: code_cells.json is not a list")
    if len(ran) != len(cells_json):
        raise PacketError(f"{run_dir}: {len(cells_json)} cells ran but the transcript shows {len(ran)} executed calls")
    cells = []
    for k, ((cid, code, res), rec) in enumerate(zip(ran, cells_json), 1):
        if code != rec.get("code"):
            raise PacketError(f"{run_dir}: cell {k} differs between code_cells.json and the transcript")
        ec, note, out, err = split_result(res)
        if ec is not None and rec.get("exit_code") is not None and ec != rec["exit_code"]:
            raise PacketError(f"{run_dir}: cell {k} exit code differs ({ec} vs {rec['exit_code']})")
        cells.append(Cell(code, ec, note, out, err))
    out_dir = run_dir / "output"
    files = sorted((p.relative_to(run_dir).as_posix(), p.stat().st_size)
                   for p in out_dir.rglob("*") if p.is_file() and not p.is_symlink()) if out_dir.is_dir() else []
    return RunView(prompt, cells, files)


def _numbered(code: str) -> str:
    lines = code.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    w = max(3, len(str(len(lines))))
    return "\n".join(f"L{n:<{w}}| {ln}" for n, ln in enumerate(lines, 1))


def line_counts(view: RunView) -> dict[int, int]:
    out = {}
    for k, c in enumerate(view.cells, 1):
        lines = c.code.split("\n")
        out[k] = len(lines) - (1 if lines and lines[-1] == "" else 0)
    return out


def render(view: RunView) -> str:
    parts = ["# Run record", "", "## Task prompt", "", view.prompt.rstrip("\n"), "", "## Code cells, in the order they ran", ""]
    if not view.cells:
        parts += ["(no code cell ran)", ""]
    for k, c in enumerate(view.cells, 1):
        parts += [f"=== Cell C{k} (exit code {c.exit_code if c.exit_code is not None else 'not shown'}) ===",
                  "--- code ---", _numbered(c.code)]
        if c.note:
            parts += ["--- note shown to the agent ---", clip(c.note)]
        parts += ["--- stdout ---", clip(c.stdout).rstrip("\n") or "(empty)",
                  "--- stderr ---", clip(c.stderr).rstrip("\n") or "(empty)", ""]
    parts += ["## Files the run wrote (final sizes)", ""]
    parts += [f"- {p}: {n} bytes" for p, n in view.files] or ["(none)"]
    return "\n".join(parts) + "\n"


class Sanitiser:
    """Identifier replacement with ONE token map for a whole packet: every identifier (string -> kind in
    TOKEN_KINDS) is replaced case-insensitively, longest first, by `<KIND>_<A,B,...>` in order of first
    appearance across all the texts it is applied to (ENDPOINT kinds by the single token ENDPOINT); then
    endpoints and credentials (`sanitise_endpoints`, `sanitise_tokens`). Applied to each source field
    BEFORE clipping, so a clip can never cut an identifier or a token into pieces that escape."""

    def __init__(self, identifiers: dict[str, str]):
        for v, kind in identifiers.items():
            if kind not in TOKEN_KINDS:
                raise ValueError(f"identifier kind {kind!r} is not one of {TOKEN_KINDS}")
        items = sorted(((v, k) for v, k in identifiers.items() if v and len(v) >= 2), key=lambda x: (-len(x[0]), x[0]))
        self.pat = re.compile("|".join(_ident_pattern(v) for v, _ in items), re.I) if items else None
        self.lower = {v.lower(): k for v, k in items}
        self.used: dict[str, str] = {}
        self.counts: dict[str, int] = {}

    def _sub(self, m: re.Match) -> str:
        key = m.group(0).lower()
        if key not in self.used:
            kind = self.lower[key]
            if kind == "ENDPOINT":
                self.used[key] = ENDPOINT
            else:
                self.counts[kind] = self.counts.get(kind, 0) + 1
                self.used[key] = f"{kind}_{_letters(self.counts[kind])}"
        return self.used[key]

    def identifiers_only(self, text: str) -> str:
        return self.pat.sub(self._sub, text) if self.pat else text

    def __call__(self, text: str) -> str:
        return sanitise_tokens(sanitise_endpoints(self.identifiers_only(text)))


def sanitise(text: str, identifiers: dict[str, str]) -> tuple[str, dict[str, str]]:
    """Identifiers only (see Sanitiser). Returns (text, identifier -> token used)."""
    s = Sanitiser(identifiers)
    return s.identifiers_only(text), s.used


_URL_HOST = re.compile(r"(?P<scheme>\b[a-z][a-z0-9+.-]*://)(?:[^@/\s'\"]*@)?(?P<host>\[[0-9a-f:]+\]|[^/\s'\":?#]+)(?:\:\d+)?", re.I)
_IPV4 = re.compile(r"(?<![\w.])(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?:\:\d{1,5})?(?!\w)(?!\.\d)")
_LOCALHOST = re.compile(r"\blocalhost(?:\:\d{1,5})?\b", re.I)
# host names that embed an address or name the platform's domain, whether or not a caller listed them
_HOSTNAME = re.compile(r"\b[\w.-]+\.(?:sslip\.io|nip\.io|site_ay-platform\.eu)(?:\:\d{1,5})?\b", re.I)
_ENDPOINT_PORT = re.compile(ENDPOINT + r":\d{1,5}\b")


# Onedata access tokens (macaroons, "MDAx..." base64) are credentials: a printed one is replaced in every packet
# before any text leaves the host, so no coder (a third-party API) ever receives one.
_TOKEN = re.compile(r"MDAx[A-Za-z0-9_\-]{16,}")
TOKEN = "TOKEN"


def sanitise_tokens(text: str) -> str:
    return _TOKEN.sub(TOKEN, text)


def sanitise_endpoints(text: str) -> str:
    """Every endpoint becomes ENDPOINT, in real and known-answer packets alike: a web URL's scheme, host and port,
    an IPv4 address with or without a port, `localhost`, and a port left after a host the identifiers
    already replaced. Paths after the host are kept (they name the dataset as the code does)."""
    # the scheme of a web URL goes too: the platform is reached over https, a local stand-in may answer over http
    text = _URL_HOST.sub(lambda m: ENDPOINT if re.match(r"(?:https?|wss?)://", m.group("scheme"), re.I)
                         else m.group("scheme") + ENDPOINT, text)
    text = _IPV4.sub(ENDPOINT, text)
    text = _LOCALHOST.sub(ENDPOINT, text)
    text = _HOSTNAME.sub(ENDPOINT, text)
    return _ENDPOINT_PORT.sub(ENDPOINT, text)


def _ident_pattern(v: str) -> str:
    """An identifier that starts or ends with a word character must not be part of a longer word:
    the model name 'glm' must not rewrite 'glmnet'."""
    p = re.escape(v)
    if re.match(r"\w", v):
        p = r"(?<![A-Za-z0-9])" + p
    if re.search(r"\w$", v):
        p = p + r"(?![A-Za-z0-9])"
    return p


def _letters(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


_LABELWORD = r"['\"]?(?:complete|omitting|unknown|omission)"
_Q = r"['\"]?"
BLOCKING = [
    (re.compile(r"\bK[- ]?test\b", re.I), "set name"),
    # a known-answer case id, its suffix included (science, #76, 2 Nov 04:50Z): the suffix may encode the answer
    (re.compile(r"\bP\d{2,}-[A-Z]\b"), "case id"),
    (re.compile(r"\bknown[- ]answers?\b", re.I), "answer-key words"),
    (re.compile(r"\bset[ _-]?[RCK]\b", re.I), "set name"),
    # a set record: {"set": "C"}, set = 'K', 'set': "r"
    (re.compile(_Q + r"\bset" + _Q + r"\s*[:=]\s*['\"]?[RCK]['\"]?(?![A-Za-z0-9_])", re.I), "set record"),
    (re.compile(_Q + r"(?:label|omission_label|truth|instrument_label)" + _Q + r"\s*[:=]\s*" + _LABELWORD, re.I),
     "label record"),
    # an answer-key assertion, as prose, a variable or a dict key, in either quote style:
    # "expected answer: complete", {"expected_answer": "complete"}, ground_truth = 'omitting', true label is unknown
    (re.compile(r"\b(?:expected|true|correct|right)[ _-]?(?:answer|label|verdict|outcome)" + _Q
                + r"\s*(?:is|[:=])\s*" + _LABELWORD, re.I), "answer-key assertion"),
    (re.compile(r"\bground[ _-]?truth" + _Q + r"\s*(?:is|[:=])\s*" + _LABELWORD, re.I), "answer-key assertion"),
]
# Tells of the local simulation the known-answer cases run on (science, #76, 20:57Z): blocked in EVERY packet.
SIM_TELLS = [
    (re.compile(r"rangefs|httpserve|mock_?onedata|icsa\.instruments\.sim\b|\bdryshim\b|_DryOnedata|"
                r"onezone\.mock|provider\.mock|\b(?:sp|pr)mock\w*|stub-dir|mount_stub|"
                r"\bmock[-_](?:provider|zone|read|token|space)\w*|\bMockOnedata\b|real_id_mock|"
                r"local-sim-read-only-token|\blocal-sim\b|stub://host-18.invalid\bStubAdapter\b|\bstub[-_]model\b", re.I), "simulation tell"),
]
# Printed durations differ between the local simulation and the platform: a cue in every packet,
# and so a refusal in a known-answer packet (strict).
TIMING = (re.compile(r"(?<![\w.])\d+(?:\.\d+)?[ \t]?(?:s|sec|secs|seconds|ms|min|mins|minutes)\b(?![\w/])"
                     r"|(?<![\w:.])\d{1,3}:\d{2}:\d{2}(?:\.\d+)?(?![\w:])"
                     r"|(?<![\w:.])\d{1,2}:\d{2}(?:\.\d+)?(?![\w:])", re.I), "printed duration")
REVIEW = [
    (re.compile(r"\bground[- ]truth\b", re.I), "answer-key words"),
    (re.compile(r"\bexpected (answer|label|verdict|outcome)\b", re.I), "answer-key words"),
    (re.compile(r"\binspection\b", re.I), "procedure word"),
    (re.compile(r"\bcoders?\b", re.I), "procedure word"),
    (re.compile(r"\bhypothes[ie]s\b", re.I), "hypothesis word"),
    (re.compile(r"\bomit(?:ting|ted|s|)\b|\bomissions?\b", re.I), "omission word"),
    (re.compile(r"\b(?:in)?complete(?:ness)?\b", re.I), "completeness word"),
    (re.compile(r"\binstrument\w*\b", re.I), "instrument word"),
    (re.compile(r"\bexpect(?:ed)?\b", re.I), "expectation word"),
    (re.compile(r"\bassert\b"), "assertion"),
    (re.compile(r"\bunknown\b", re.I), "label word"),
    (re.compile(r"\b(?:truth|known|missing|verdict|label)\b", re.I), "answer-key word"),
]
# The report key the task prompt itself requires (every run writes it): never a cue, even in strict mode.
REPORT_KEY = re.compile(r"""['"]complete['"]\s*:""")


def scan(text: str, identifiers: dict[str, str] = (), prompt: str = "", outputs: str | None = None) -> dict:
    """Cues left in a rendered packet. BLOCKING cues are searched in the WHOLE text, the task prompt
    included. REVIEW cues skip the task prompt's own text (it says 'complete' and 'expected' in every
    run) and the report key "complete" the prompt requires."""
    blocking, review = [], []
    for v in identifiers or {}:
        if v and re.search(_ident_pattern(v), text, re.I):
            blocking.append({"cue": "residual identifier", "kind": dict(identifiers)[v]})
    for rx, why in BLOCKING + SIM_TELLS:
        for m in rx.finditer(text):
            blocking.append({"cue": why, "text": m.group(0)})
    for rx in (_URL_HOST, _IPV4, _LOCALHOST, _HOSTNAME):
        for m in rx.finditer(text):
            if ENDPOINT not in m.group(0):
                blocking.append({"cue": "endpoint not sanitised", "text": "(host)"})
    body = text.replace(prompt, "") if prompt else text
    body = REPORT_KEY.sub(":", body)
    for rx, why in REVIEW:
        for m in rx.finditer(body):
            review.append({"cue": why, "text": m.group(0)})
    # a duration is something PRINTED: looked for in the cells' outputs only (code has slices such as 10:20)
    rx, why = TIMING
    for m in rx.finditer(body if outputs is None else outputs):
        review.append({"cue": why, "text": m.group(0)})
    return {"blocking": blocking, "review": review}


def build(run_dir, identifiers: dict[str, str], *, strict: bool = False) -> dict:
    """Render, sanitise and scan one run. Returns {'text', 'sha256', 'lines', 'tokens', 'cues', 'cells'}.
    Raises PacketError if a blocking cue survives, or, with `strict` (K-test packets, whose code we
    wrote), if ANY review cue does: a known-answer case must carry no cue at all."""
    view = read_run(run_dir)
    # simulation tells are looked for in the RAW, unclipped fields first: sanitising would turn a mock's host
    # name into ENDPOINT, and a clip could cut a tell in two
    raw_all = "\n".join([view.prompt] + [x for c in view.cells for x in (c.code, c.note, c.stdout, c.stderr)]
                         + [p for p, _ in view.files])
    raw_tells = [{"cue": why, "text": m.group(0)} for rx, why in SIM_TELLS for m in rx.finditer(raw_all)]
    if raw_tells:
        raise PacketError(f"{run_dir}: simulation tells in the packet: {raw_tells[:5]}")
    san = Sanitiser(identifiers)
    dur = sanitise_durations
    clean = RunView(san(view.prompt),
                    [Cell(san(c.code), c.exit_code, dur(san(c.note)), dur(san(c.stdout)), dur(san(c.stderr))) for c in view.cells],
                    [(san(p), n) for p, n in view.files], view.warnings)
    text = san(render(clean))              # a second pass is idempotent; it catches anything rendering joined
    used = san.used
    prompt_s = clean.prompt.rstrip("\n")
    outputs = "\n".join(x for c in clean.cells for x in (c.note, c.stdout, c.stderr))
    cues = scan(text, identifiers, prompt=prompt_s, outputs=outputs)
    if cues["blocking"]:
        raise PacketError(f"{run_dir}: blocking cues in the packet: {cues['blocking'][:5]}")
    if strict and cues["review"]:
        raise PacketError(f"{run_dir}: cues in a known-answer packet: {cues['review'][:5]}")
    return {"text": text, "sha256": hashlib.sha256(text.encode()).hexdigest(), "lines": line_counts(view),
            "tokens": sorted(set(used.values())), "cues": cues, "cells": len(view.cells)}
