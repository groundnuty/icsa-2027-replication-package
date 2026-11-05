"""The two blind coders (rubric §4) and the per-packet attempt loop with its archive.

A coder backend is an object with `.coder`, `.model`, `.effort` and `.call(message, schema)`, which returns a
`CallResult`. `code_packet` sends the identical message to a backend in a fresh context for up to
`max_attempts` attempts, archives every attempt, and writes `final.json`. A malformed answer never
becomes a verdict: the final status is then "malformed" and the answer null.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import answer, isolation, prompt, secretscan

FORMAT_ANSWER = "icsa-inspection-answer-v1"
ANTHROPIC_KEY_PATH = "~/.secrets/icsa-2027/anthropic.key"
# The two coders: one model and one effort each. A change is one line here (the coder model is registered: science rules it).
CODEX_MODEL, CODEX_EFFORT = "gpt-6.1-sol", "high"        # amendment 23 (science, #76, 2 Nov 15:03Z); was gpt-6-astra
CLAUDE_MODEL, CLAUDE_EFFORT = "claude-opus-5-5", "high"
# The fallback pair's second coder (amendment 26, science, #76, 23:23Z): Opus + Sonnet, where the plan's Codex quota runs out. It may
# never code a Sonnet run: a subject model does not judge its own runs.
SONNET_MODEL, SONNET_EFFORT = "site_j", "high"
CLAUDE_MAX_TOKENS = 64000       # the request's max_tokens, thinking included: the most one call can output (the campaign's spend bound reads it)
CODEX_TIMEOUT_S = 1800
# Features a blind coder must not have (codex 0.166.0, `codex features list`, 2 Nov): through host-15.invalid, the model host the
# proxy must allow, `apps` opens an MCP channel to the account's connected apps (seen as backend-api/ps/mcp even with
# --ignore-user-config), and plugins, browser and computer use, image generation and shell would let it act. The container
# stays the boundary; these remove the means. The canary turns shell back on for its positive control only.
CODEX_DISABLE = ("apps", "plugins", "remote_plugin", "plugin_discovery_prefetch", "browser_use", "browser_use_external",
                 "browser_use_full_cdp_access", "computer_use", "image_generation", "in_app_browser", "skill_mcp_dependency_install",
                 "skill_search", "tool_suggest", "hooks", "multi_agent", "shell_tool", "unified_exec", "code_mode_host",
                 "guardian_approval", "plugin_sharing")
# Features codex 0.166.0 enables by default that were reviewed and left on (none acts on the world or opens a channel; the
# shell, exec helpers and every tool feature above are off). Any OTHER default-enabled feature, as a codex update may add,
# stops the run before any call (science, #2, 14:55Z: the apps channel must not come back with an update).
CODEX_REVIEWED_ENABLED = frozenset("""api_key_cyber_access_programs api_key_model_discovery auth_elicitation bedrock_setup_wizard
    browser_annotation_api cli_daybreak code_mode_interrupt collaboration_modes compaction_image_budget content_item_kinds
    daemon_auto_start enable_request_compression fast_mode goals guardian_reuse_parent_compaction in_app_chat
    in_app_dictation in_app_local_automation in_app_updates in_app_voice incremental_tools instant_interrupt item_ids
    mcp_oauth_refresh_coordination mentions_v2 prediction_preserve_parent_tools realtime_conversation reasoning_effort_override
    resize_all_images shell_snapshot sleep_tool sqlite steer system_proxy_fallback terminal_resize_reflow
    tool_call_mcp_elicitation tool_search_always_defer_mcp_tools tui_app_server ultrafast_mode unbounded_connection_retries
    unified_exec_tty view_image workspace_dependencies worktrees write_stdin_approval""".split())
CODEX_CONFIG = ('web_search="disabled"',)
# Values that must never reach an archive: scanned for exactly (plus token shapes) in everything a coder returns.
SECRET_FILES = (ANTHROPIC_KEY_PATH, "~/.agent_framework/keys/handle_4/handle_5.pem")

# USD per million tokens, from the claude-api skill's model table (cached 2026-10-06); a cache write (5-minute) is 1.25x input.
CLAUDE_PRICES_BY_MODEL = {
    "claude-opus-5-5": {"input": 4.0, "output": 20.0, "cache_read": 0.20, "cache_write": 5.0},
    "site_j": {"input": 2.0, "output": 10.0, "cache_read": 0.20, "cache_write": 2.50},
}

# Codex JSONL item types that mean the coder acted on the world instead of only answering.
FORBIDDEN_ITEM_TYPES = {"command_execution", "file_change", "mcp_tool_call", "web_search"}
# A coder is blind and alone: a subagent it spawned would break that (science, #2, 2 Nov 11:54Z). Measured on gpt-6-astra, codex 0.166.0, 2 Nov: nothing turns it off.
# `spawn_agent` stays in the model's tools, and a spawn succeeds, with features.multi_agent=false and with agents.max_threads=1, while the event stream shows only a later wait.
# So each call has a fresh CODEX_HOME, in which more than one session file means a subagent ran, whatever the stream showed, and the answer is contaminated. An event that names
# one is too. Measured the same day through this backend: told to spawn, 2 sessions, contaminated; a plain call, 1 session, ok.
SUBAGENT_EVENT_WORDS = ("collab", "spawn", "subagent", "sub_agent", "multi_agent")
# Registered rule 21(a) (#2, 14:28Z): at most 3 attempts per coder and packet; retry only when an attempt was
# contaminated, malformed, or failed by infrastructure ("error"); use the first valid answer, never selected on content;
# otherwise the coder's verdict is CANNOT TELL (report.py). A refusal is none of these: it ends the coder's attempts.
RETRY_ON = ("contaminated", "malformed", "error")
USAGE_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens")


@dataclass
class CallResult:
    text: str = ""
    status: str = "ok"          # ok | contaminated | refused | error
    usage: dict = field(default_factory=dict)
    detail: dict = field(default_factory=dict)   # exit code, stop_reason, error text, ...
    archive: dict = field(default_factory=dict)  # file name -> text (events.jsonl, response.json)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


# --------------------------------------------------------------------------- Codex

def _names_a_subagent(event_type) -> bool:
    return isinstance(event_type, str) and any(w in event_type for w in SUBAGENT_EVENT_WORDS)


def scan_codex_events(raw: str) -> dict:
    """Parse a Codex `--json` stream: item types seen, forbidden ones, last usage, agent text."""
    types, bad, usage, agent_text, errors = [], [], {}, None, []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            ev = json.loads(ln)
        except json.JSONDecodeError:
            errors.append(f"unparsable event line: {ln[:80]!r}")
            continue
        et = ev.get("type")
        types.append(et)
        item = ev.get("item") if isinstance(ev.get("item"), dict) else None
        if item:
            it = item.get("type")
            types.append(f"{et}:{it}")
            if it in FORBIDDEN_ITEM_TYPES or _names_a_subagent(it):
                bad.append(it)
            if it == "agent_message" and et == "item.completed":
                agent_text = item.get("text")
        if et in FORBIDDEN_ITEM_TYPES or _names_a_subagent(et):
            bad.append(et)
        if et == "turn.completed" and isinstance(ev.get("usage"), dict):
            u = ev["usage"]
            usage = {"input_tokens": u.get("input_tokens", 0), "cached_input_tokens": u.get("cached_input_tokens", 0),
                     "output_tokens": u.get("output_tokens", 0),
                     "reasoning_tokens": u.get("reasoning_output_tokens", u.get("reasoning_tokens", 0))}
    return {"types": sorted(set(t for t in types if t)), "forbidden": sorted(set(bad)), "usage": usage,
            "agent_text": agent_text, "errors": errors}


# A Codex call that failed because the ChatGPT plan's window is used up (amendment 26: the plan's quota gate, `plan.py`). BEST EFFORT: the text is
# a guess, and the gate does not depend on it (a run of failed calls with no quota reading closes it as blind). NOT verified against a
# real limit response: none was captured when this was written (the account's limit of 2 Nov was not logged), so it is one narrow
# function over the stream's error messages and stderr. It is applied only to an attempt that already failed (status "error"), and reads
# error messages only: never an answer, a verdict or any content of the packet. The benign error item the CLI prints for a disabled code-mode
# host ("Code Mode is unavailable...") matches none of it.
QUOTA_PATTERNS = tuple(re.compile(p, re.I) for p in (
    r"usage[ _-]?limit", r"hit your .{0,40}limit", r"rate[ _-]?limit(?:ed| exceeded| reached)", r"limit[ _]reached",
    r"insufficient[ _]quota", r"exceeded your .{0,40}(?:quota|limit)", r"quota (?:exceeded|exhausted)", r"too many requests",
    r"(?:http|status)[ :]*429"))
QUOTA_EVENT_TYPES = ("error", "turn.failed")


def quota_error(stdout: str, stderr: str) -> str | None:
    """The first error message of a failed Codex call that says the plan's usage limit is reached, shortened; else None."""
    msgs: list[str] = []
    for ln in (stdout or "").splitlines():
        try:
            ev = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict):
            continue
        item = ev.get("item") if isinstance(ev.get("item"), dict) else {}
        err = ev.get("error") if isinstance(ev.get("error"), dict) else {}
        if ev.get("type") in QUOTA_EVENT_TYPES or item.get("type") == "error":
            for v in (ev.get("message"), err.get("message"), item.get("message")):
                if isinstance(v, str):
                    msgs.append(v)
    msgs.append((stderr or "")[-4000:])
    for m in msgs:
        if any(p.search(m) for p in QUOTA_PATTERNS):
            return " ".join(m.split())[:200]
    return None


def stderr_header(stderr: str) -> dict:
    """The `model:` and `reasoning effort:` lines codex prints at the start of stderr (cited with every verdict)."""
    out = {}
    for ln in stderr[:8000].splitlines():
        k, _, v = ln.partition(":")
        k = k.strip().lower()
        if k in ("model", "reasoning effort", "provider", "sandbox") and v.strip() and k not in out:
            out[k] = v.strip()
    return out


def rollout_context(home: Path) -> dict:
    """Model and effort as codex recorded them in its session file (`turn_context`): with --json it prints no stderr header,
    so this is the per-answer evidence of what ran. Scalar fields only; several turns with different values are all kept."""
    seen: dict[str, list] = {}
    for f in sorted(Path(home).glob("sessions/**/rollout-*.jsonl")):
        for ln in f.read_text(errors="replace").splitlines():
            try:
                ev = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if not isinstance(ev, dict):
                continue
            pl = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
            # the plan's rate-limit use as codex last saw it (record only: for the campaign's throughput plan)
            if ev.get("type") == "event_msg" and pl.get("type") == "token_count" and isinstance(pl.get("rate_limits"), dict):
                flat = {}
                for k, v in pl["rate_limits"].items():
                    if isinstance(v, dict):
                        flat.update({f"{k}.{k2}": v2 for k2, v2 in v.items() if isinstance(v2, (str, int, float, bool))})
                    elif isinstance(v, (str, int, float, bool)):
                        flat[k] = v
                seen["rate_limits"] = [flat]
                continue
            if ev.get("type") not in ("turn_context", "session_meta"):
                continue
            for k in ("model", "effort", "reasoning_effort", "model_provider", "cli_version", "approval_policy"):
                v = pl.get(k)
                if isinstance(v, (str, int, float, bool)) and v not in seen.setdefault(k, []):
                    seen[k].append(v)
    return {k: (v[0] if len(v) == 1 else v) for k, v in seen.items() if v}


def codex_features(codex_bin: str) -> dict[str, bool]:
    """Every feature codex knows and whether it is on by default (run with an empty CODEX_HOME, so no user config)."""
    with tempfile.TemporaryDirectory(prefix="codex-features-") as home:
        p = subprocess.run([codex_bin, "features", "list"], capture_output=True, text=True, timeout=60,
                           env={"PATH": "/usr/bin:/bin", "HOME": home, "CODEX_HOME": home})
    if p.returncode != 0:
        raise isolation.IsolationError(f"codex features list failed ({p.returncode})")
    out = {}
    for ln in p.stdout.splitlines():
        f = ln.split()
        if len(f) >= 2 and f[-1] in ("true", "false"):
            out[f[0]] = f[-1] == "true"
    if not out:
        raise isolation.IsolationError("codex features list gave no features")
    return out


def check_codex_features(features: dict[str, bool], disable=None) -> dict:
    """Refuse a codex whose defaults differ from what was reviewed: a feature on by default that is neither disabled for the
    coder nor reviewed, or a feature the coder disables that no longer exists (a rename would leave it on)."""
    disable = set(CODEX_DISABLE if disable is None else disable)
    new = sorted(f for f, on in features.items() if on and f not in disable and f not in CODEX_REVIEWED_ENABLED)
    gone = sorted(f for f in disable if f not in features)
    if new or gone:
        raise isolation.IsolationError(f"codex features differ from the reviewed set: on and unreviewed {new}, "
                                       f"disabled but unknown {gone}")
    return {"enabled_after_disable": sorted(f for f, on in features.items() if on and f not in disable)}


class CodexBackend:
    """Each call runs inside `isolation.DockerLauncher` (a container that reads only its own call's files and reaches only
    the model API). `launcher` is replaceable for tests only; nothing in this package launches codex any other way."""
    coder, model, effort = "codex", CODEX_MODEL, CODEX_EFFORT

    def __init__(self, timeout_s: int = CODEX_TIMEOUT_S, codex_bin: str | None = None, *, launcher=None,
                 sandbox: str = "read-only", secret_files: tuple[str, ...] | None = None,
                 disable: tuple[str, ...] = CODEX_DISABLE, config: tuple[str, ...] = CODEX_CONFIG):
        self.timeout_s, self.sandbox, self.disable, self.config = timeout_s, sandbox, tuple(disable), tuple(config)
        self.launcher = launcher or isolation.DockerLauncher(codex_bin)
        self.secret_files = tuple(secret_files) if secret_files is not None else SECRET_FILES

    def preflight(self) -> dict:
        out = self.launcher.preflight() if hasattr(self.launcher, "preflight") else {}
        if isinstance(self.launcher, isolation.DockerLauncher):
            out["features"] = check_codex_features(codex_features(self.launcher.codex_bin), self.disable)
        return out

    def argv(self, schema: bool = True) -> list[str]:
        # not --ephemeral: the session files in CODEX_HOME are the proof no subagent ran
        feats = [a for f in self.disable for a in ("--disable", f)] + [a for c in self.config for a in ("-c", c)]
        return ["exec", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check", "-s", self.sandbox, *feats,
                "-m", self.model, "-c", f'model_reasoning_effort="{self.effort}"', "-C", "{CWD}",
                *(["--output-schema", "{IO}/schema.json"] if schema else []), "--json", "-o", "{IO}/last.txt", "-"]

    def probe(self, message: str = "Reply with the single word: ok") -> CallResult:
        """Read the plan's quota (science, #76, 3 Nov 00:02Z): a one-line message through the same isolated launcher, with no output schema. It has
        no packet and is never a coder answer; its tokens are the caller's to log apart. Its rate-limit reading is `detail["ran"]["rate_limits"]`."""
        return self.call(message, None)

    def call(self, message: str, schema: dict | None) -> CallResult:
        with tempfile.TemporaryDirectory(prefix="inspect-io-") as io, \
                tempfile.TemporaryDirectory(prefix="inspect-home-") as home:
            home_p, io_p = Path(home), Path(io)
            if schema is not None:
                (io_p / "schema.json").write_text(json.dumps(schema))
            sha_at_copy = self.launcher.seed_home(home_p)
            exact = secretscan.exact_values_from_files([*self.secret_files, str(home_p / "auth.json")])
            try:
                r = self.launcher.run(self.argv(schema is not None), message, home_p, io_p, self.timeout_s)
            finally:
                # a login refreshed during the call holds new values: they are scanned for too (Codex review, 2 Nov)
                exact = [*exact, *secretscan.exact_values_from_files([str(home_p / "auth.json")])]
                login = self.launcher.settle_login(home_p, sha_at_copy)
                (home_p / "auth.json").unlink(missing_ok=True)      # the login copy never outlives the call
            last = (io_p / "last.txt").read_text() if (io_p / "last.txt").exists() else ""
            sessions = len(list(home_p.glob("sessions/**/rollout-*.jsonl")))
            ran = rollout_context(home_p)
        found = {}

        def clean(name: str, text: str) -> str:
            t, hits = secretscan.redact(text or "", exact)
            if hits:
                found[name] = len(hits)
            return t

        stdout, stderr, last = clean("events", r.stdout), clean("stderr", r.stderr), clean("answer", last)
        archive = {"events.jsonl": stdout, "stderr.txt": stderr,
                   **{k: clean(k, v) for k, v in r.archive.items()}}
        detail = {"argv": self.argv(schema is not None), "exit_code": r.returncode, "stderr_tail": stderr[-2000:], "stderr_header": stderr_header(stderr),
                  "sessions": sessions, "ran": ran, "proxy": json.loads(clean("proxy_meta", json.dumps(r.proxy))), **login}
        if found:
            detail["secret_findings"] = found
        ev = scan_codex_events(stdout)
        text = last if last.strip() else (ev["agent_text"] or "")
        detail["event_types"] = ev["types"]
        status = "ok"
        # contamination is looked for FIRST, a timed-out call included: a subagent that ran before the timeout still counts
        # toward the spawn rate (final pinned pass S5, 2 Nov)
        if ev["forbidden"] or sessions > 1:
            status, detail["forbidden_events"] = "contaminated", ev["forbidden"] + ([f"{sessions} sessions: a subagent ran"] if sessions > 1 else [])
            detail["subagent"] = sessions > 1 or any(_names_a_subagent(x) for x in ev["forbidden"])
            if r.timed_out:
                detail["timed_out"] = True
        elif r.timed_out:
            return CallResult(status="error", usage=ev["usage"], detail={**detail, "error": f"timeout after {self.timeout_s}s"},
                              archive=archive)
        elif r.returncode != 0:
            status, detail["error"] = "error", f"codex exit {r.returncode}"
        elif sessions == 0:
            status, detail["error"] = "error", "no session file: whether a subagent ran cannot be seen"
        if status == "error":
            q = quota_error(stdout, stderr)
            if q:
                detail["quota_error"] = q       # recorded per attempt: the plan's quota gate and its fallback read it (plan.py)
        return CallResult(text=text, status=status, usage=ev["usage"], detail=detail, archive=archive)


# --------------------------------------------------------------------------- Claude

def _read_key(path: str = ANTHROPIC_KEY_PATH) -> str:
    return Path(path).read_text().strip()


def claude_cost(u: dict, model: str = CLAUDE_MODEL) -> float | None:
    """None for a model with no price in the table: a cost is never computed at another model's prices."""
    p = CLAUDE_PRICES_BY_MODEL.get(model)
    if p is None:
        return None
    return (u.get("input_tokens", 0) * p["input"] + u.get("output_tokens", 0) * p["output"]
            + u.get("cache_read_input_tokens", 0) * p["cache_read"]
            + u.get("cache_creation_input_tokens", 0) * p["cache_write"]) / 1e6


class ClaudeBackend:
    coder, model, effort = "claude", CLAUDE_MODEL, CLAUDE_EFFORT

    def __init__(self, key_path: str = ANTHROPIC_KEY_PATH):
        self.key_path = key_path

    def call(self, message: str, schema: dict) -> CallResult:
        import anthropic
        key = _read_key(self.key_path)

        def scrub(s: str) -> str:
            return s.replace(key, "[KEY]") if key else s

        try:
            client = anthropic.Anthropic(api_key=key, max_retries=4)
            with client.messages.stream(
                    model=self.model, max_tokens=CLAUDE_MAX_TOKENS, thinking={"type": "adaptive"},
                    output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": schema}},
                    messages=[{"role": "user", "content": message}]) as stream:
                msg = stream.get_final_message()
        except anthropic.RateLimitError as e:
            return CallResult(status="error", detail={"error": scrub(f"RateLimitError: {e}")})
        except anthropic.APIStatusError as e:
            return CallResult(status="error", detail={"error": scrub(f"APIStatusError {e.status_code}: {e}")})
        except anthropic.APITimeoutError as e:      # a subclass of APIConnectionError, so first: a timed-out call may have been partly billed, a refused connection was not
            return CallResult(status="error", detail={"error": scrub(f"APITimeoutError: {e}")})
        except anthropic.APIConnectionError as e:
            return CallResult(status="error", detail={"error": scrub(f"APIConnectionError: {e}")})
        d = msg.to_dict()
        uo = getattr(msg, "usage", None)
        usage = {"input_tokens": getattr(uo, "input_tokens", 0) or 0, "output_tokens": getattr(uo, "output_tokens", 0) or 0,
                 "cache_creation_input_tokens": getattr(uo, "cache_creation_input_tokens", 0) or 0,
                 "cache_read_input_tokens": getattr(uo, "cache_read_input_tokens", 0) or 0}
        detail = {"stop_reason": msg.stop_reason}
        sd = getattr(msg, "stop_details", None)
        if sd is not None:
            detail["stop_details"] = sd if isinstance(sd, (dict, str)) else getattr(sd, "to_dict", lambda: str(sd))()
        arch = {"response.json": scrub(json.dumps(d, indent=1, default=str))}
        if msg.stop_reason == "refusal":
            return CallResult(status="refused", usage=usage, detail=detail, archive=arch)
        if msg.stop_reason != "end_turn":
            detail["error"] = f"stop_reason {msg.stop_reason}"
            return CallResult(status="error", usage=usage, detail=detail, archive=arch)
        text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
        return CallResult(text=text, usage=usage, detail=detail, archive=arch)


# --------------------------------------------------------------------------- the Codex coder through the OpenAI API
# Science, #76, 18:42Z: if the operator picks the API for the Codex coder, it is a plain Responses API call, like the Claude
# coder: the same model and effort, the same message and schema, no tools, no Codex agent instructions. It needs no container
# (it can act on nothing). Prepared and tested on stand-ins; unused until a key exists at OPENAI_KEY_PATH.
OPENAI_KEY_PATH = "~/.secrets/icsa-2027/openai.key"


def _openai_client(key: str):
    import openai
    return openai.OpenAI(api_key=key, max_retries=4, timeout=CODEX_TIMEOUT_S)


def _as_dict(obj) -> dict:
    for name in ("to_dict", "model_dump"):
        f = getattr(obj, name, None)
        if callable(f):
            return f()
    return obj if isinstance(obj, dict) else {}


class OpenAIApiBackend:
    coder, model, effort = "codex", CODEX_MODEL, CODEX_EFFORT

    def __init__(self, key_path: str = OPENAI_KEY_PATH, client_factory=_openai_client):
        self.key_path, self.client_factory = key_path, client_factory

    def preflight(self) -> dict:
        if not Path(self.key_path).is_file():
            raise isolation.IsolationError(f"no OpenAI key at {self.key_path}: the API coder cannot run")
        return {"client": "openai-responses-api", "model": self.model, "effort": self.effort}

    def call(self, message: str, schema: dict) -> CallResult:
        import openai
        key = _read_key(self.key_path)

        def scrub(t: str) -> str:
            return t.replace(key, "[KEY]") if key else t

        detail = {"client": "openai-responses-api"}
        try:
            resp = self.client_factory(key).responses.create(
                model=self.model, input=message, reasoning={"effort": self.effort}, tools=[], store=False,
                text={"format": {"type": "json_schema", "name": "inspection_answer", "schema": schema, "strict": True}})
        except openai.RateLimitError as e:
            return CallResult(status="error", detail={**detail, "error": scrub(f"RateLimitError: {e}")})
        except openai.APIStatusError as e:
            return CallResult(status="error", detail={**detail, "error": scrub(f"APIStatusError {e.status_code}: {e}")})
        except (openai.APIConnectionError, openai.APITimeoutError) as e:
            return CallResult(status="error", detail={**detail, "error": scrub(f"{type(e).__name__}: {e}")})
        d = _as_dict(resp)
        u = d.get("usage") or {}
        usage = {"input_tokens": u.get("input_tokens", 0) or 0,
                 "cached_input_tokens": (u.get("input_tokens_details") or {}).get("cached_tokens", 0) or 0,
                 "output_tokens": u.get("output_tokens", 0) or 0,
                 "reasoning_tokens": (u.get("output_tokens_details") or {}).get("reasoning_tokens", 0) or 0}
        detail.update(response_status=d.get("status"), ran={"model": d.get("model"),
                                                           "effort": (d.get("reasoning") or {}).get("effort")})
        arch = {"response.json": scrub(json.dumps(d, indent=1, default=str))}
        parts = [c for item in d.get("output") or [] if isinstance(item, dict) for c in item.get("content") or []
                 if isinstance(c, dict)]
        if any(c.get("type") == "refusal" for c in parts):
            return CallResult(status="refused", usage=usage, detail=detail, archive=arch)
        if d.get("status") != "completed":
            detail["error"] = f"response status {d.get('status')}: {(d.get('incomplete_details') or {}).get('reason')}"
            return CallResult(status="error", usage=usage, detail=detail, archive=arch)
        text = "".join(c.get("text", "") for c in parts if c.get("type") == "output_text")
        return CallResult(text=text, usage=usage, detail=detail, archive=arch)


class SonnetBackend(ClaudeBackend):
    """The same plain API call as the Opus coder, with no tools: the same prompt and schema, another model."""
    coder, model, effort = "sonnet", SONNET_MODEL, SONNET_EFFORT


def default_backends(codex_client: str = "cli", coders=("codex", "claude", "sonnet")) -> dict:
    """Only the coders asked for: the Codex coder through its CLI in the isolation container ("cli") or through the OpenAI API ("api"),
    Opus, Sonnet. A Claude-only run needs no codex binary on its host."""
    if codex_client not in ("cli", "api"):
        raise ValueError(f"codex_client must be cli or api, not {codex_client!r}")
    make = {"codex": CodexBackend if codex_client == "cli" else OpenAIApiBackend, "claude": ClaudeBackend, "sonnet": SonnetBackend}
    return {c: make[c]() for c in coders}


# --------------------------------------------------------------------------- attempt loop

def _norm_usage(u: dict) -> dict:
    """Summable usage: Claude's cache read counts as cached input, creation stays in input."""
    return {"input_tokens": u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0),
            "cached_input_tokens": u.get("cached_input_tokens", 0) + u.get("cache_read_input_tokens", 0),
            "output_tokens": u.get("output_tokens", 0), "reasoning_tokens": u.get("reasoning_tokens", 0)}


def archive_prompt(work_dir) -> None:
    d = Path(work_dir) / "prompt"
    d.mkdir(parents=True, exist_ok=True)
    (d / "instructions.txt").write_text(prompt.instructions())
    (d / "schema.json").write_text(json.dumps(answer.schema(), indent=1, sort_keys=True))
    (d / "prompt.sha256").write_text(prompt.prompt_sha256() + "\n")


def code_packet(pid: str, packet_text: str, lines: dict[int, int], backend, work_dir, *,
                max_attempts: int = 3, codex_price_per_mtok: dict | None = None) -> dict:
    """Run one coder on one packet; archive each attempt; write and return final.json's content."""
    base = Path(work_dir) / "answers" / pid / backend.coder
    message = prompt.message(packet_text)
    msha = _sha(message)
    schema = answer.schema()
    totals = {k: 0 for k in USAGE_KEYS}
    raw_usage = {}
    wall, contaminated, errors, obj, status, n = 0.0, 0, [], None, "malformed", 0
    subagents = 0
    last_status = None

    def add_usage(usage: dict) -> None:
        u = _norm_usage(usage)
        for k in totals:
            totals[k] += u[k]
        for k, v in usage.items():
            raw_usage[k] = raw_usage.get(k, 0) + (v or 0)

    # Resume: attempts already archived count (max_attempts is a total across restarts); a directory
    # without meta.json was interrupted, is kept under another name and is not counted.
    base.mkdir(parents=True, exist_ok=True)
    done = []
    for d in sorted(base.glob("attempt-*"), key=lambda p: p.name):
        k = d.name[len("attempt-"):]
        if not k.isdigit():
            continue
        tag = None
        if (d / "meta.json").exists():
            m = json.loads((d / "meta.json").read_text())
            if (m.get("message_sha256"), m.get("model"), m.get("effort")) == (msha, backend.model, backend.effort):
                done.append((int(k), d))
            else:
                tag = "stale"  # answered another message, model or effort: never reused or counted
        else:
            tag = "interrupted"
        if tag:
            j = 1
            while (base / f"{d.name}.{tag}-{j}").exists():
                j += 1
            d.rename(base / f"{d.name}.{tag}-{j}")
    counted = len(done)
    for k, d in sorted(done):
        n = k
        meta = json.loads((d / "meta.json").read_text())
        wall += meta.get("wall_s", 0)
        add_usage(meta.get("usage", {}))
        errors = meta.get("errors", [])
        if meta["status"] == "contaminated":
            contaminated += 1
        subagents += bool(meta.get("subagent"))
        last_status = meta["status"]
        if meta["status"] == "valid" and status != "valid":     # the first valid answer, if one was archived
            parsed, perr = answer.parse((d / "raw.txt").read_text())
            if perr is None and not answer.validate(parsed, lines):
                status, obj = "valid", parsed
    stopped = any(json.loads((d / "meta.json").read_text())["status"] not in (*RETRY_ON, "valid") for _, d in done)
    if status != "valid" and not stopped:
        while counted < max_attempts:
            n += 1
            counted += 1
            d = base / f"attempt-{n}"
            d.mkdir(parents=True, exist_ok=False)
            started, t0 = _now(), time.monotonic()
            try:
                res = backend.call(message, schema)
            except isolation.IsolationError:
                raise          # the isolation could not be set up: no attempt happened, so none is counted; the runner stops
            except Exception as e:  # a backend crash is a failed attempt, never a verdict
                res = CallResult(status="error", detail={"error": f"{type(e).__name__}: {e}"})
            w = time.monotonic() - t0
            ended = _now()
            wall += w
            a_status, errs, parsed = res.status, [], None
            if a_status == "ok":
                parsed, perr = answer.parse(res.text)
                errs = [perr] if perr else answer.validate(parsed, lines)
                a_status = "malformed" if errs else "valid"
            else:
                errs = [res.detail.get("error") or f"{res.status}"]
                if res.status == "contaminated":
                    contaminated += 1
            subagents += bool(res.detail.get("subagent"))
            add_usage(res.usage)
            errors = errs
            (d / "raw.txt").write_text(res.text or "")
            for name, content in res.archive.items():
                (d / name).write_text(content)
            meta = {"status": a_status, "errors": errs, "usage": res.usage, "wall_s": round(w, 3),
                    "started_at": started, "ended_at": ended, "message_sha256": msha, "model": backend.model,
                    "effort": backend.effort, **res.detail}
            (d / "meta.json").write_text(json.dumps(meta, indent=1, default=str))
            last_status = a_status
            if a_status == "valid":
                status, obj = "valid", parsed
                break
            if a_status not in RETRY_ON:       # 21(a): a refusal is not retried
                break
    if status != "valid" and last_status not in (*RETRY_ON, "valid"):
        status = last_status                   # "refused": CANNOT TELL in the report, like every final without a valid answer
    if status != "valid" and contaminated:      # science, #76, 2 Nov 12:43Z: its verdict is CANNOT TELL (report.py), so the run stays unknown, never a guess
        status = "contaminated"
    cost, note = None, None
    if backend.coder in ("claude", "sonnet"):
        c = claude_cost(raw_usage, backend.model)
        cost = round(c, 6) if c is not None else None
        if c is None:
            note = f"no price for {backend.model}; cost not computed"
    elif codex_price_per_mtok:
        p = codex_price_per_mtok
        cost = round((totals["input_tokens"] - totals["cached_input_tokens"]) * p.get("input", 0) / 1e6
                     + totals["cached_input_tokens"] * p.get("cached_input", 0) / 1e6
                     + totals["output_tokens"] * p.get("output", 0) / 1e6, 6)
    else:
        note = "Codex price per MTok is not known; cost not computed"
    final = {"format": FORMAT_ANSWER, "packet": pid, "coder": backend.coder, "model": backend.model,
             "effort": backend.effort, "status": status, "attempts": counted, "answer": obj,
             "errors": [] if status == "valid" else errors, "prompt_sha256": prompt.prompt_sha256(),
             "message_sha256": msha, "packet_sha256": _sha(packet_text), "usage": totals, "wall_s": round(wall, 3),
             "cost_usd": cost, "contaminated_attempts": contaminated, "subagent_attempts": subagents}
    if note:
        final["cost_note"] = note
    (base / "final.json").write_text(json.dumps(final, indent=1))
    return final
