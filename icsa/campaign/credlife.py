"""Credential lifetimes, read-only (science, #34, 3 Nov 00:52Z). Names and dates only: no password, token or key value is read into a line that is printed or written.

    python -m icsa.campaign.credlife --root <campaign dir> [--probe-passwords] [--no-onezone] [--no-keys]

It reads (1) from Onezone, as the admin the slot-user code already uses (icsa/harness/slot_users.py: a temporary admin token minted with the admin password file, then GET
/users/<id>), the record of every slot user in config/slot_map.json and of the admin, and looks for a field that is an expiry of the password; (2) for the site_b and the
Anthropic key, whether the key file is there (its mode and write date) and what one authenticated GET reports (the status, and any header or JSON field that names an expiry).
`--probe-passwords` also mints, and drops, a 60-second token per slot user to show that its password opens the account today (not a lifetime).

A lifetime that cannot be read is a finding with state "unreadable", and it goes in the operator's queue (operator_queue.causes_from_status reads `credential_lifetimes.json`
from the campaign root, where this writes it). What the code cannot settle is said in each finding's `why`: whether Onezone exposes a password lifetime AT ALL is UNKNOWN until this
has run once (the field names of its user record are printed), and neither API is known to report a key's expiry on an ordinary call (Anthropic's admin API would, with an admin key
this study does not hold)."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

EXPIRY = re.compile(r"(expir|valid_?until|not_?after|lifetime|ttl|deadline)", re.I)
WARN_S = 5 * 86400.0           # a key or password that ends within this is "expiring": the campaign runs to its hard stop (hard_stop_utc in the launch config)


def _iso(x: Any) -> str | None:
    """A date as ISO, from an epoch (seconds or milliseconds) or an ISO string; None for anything else (a value that is not a date is never echoed)."""
    try:
        if isinstance(x, bool):
            return None
        if isinstance(x, (int, float)):
            v = float(x) / 1000.0 if x > 1e11 else float(x)
            return dt.datetime.fromtimestamp(v, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if v > 1e8 else None
        if isinstance(x, str) and len(x) <= 40 and re.match(r"^\d{4}-\d{2}-\d{2}", x):
            return dt.datetime.fromisoformat(x.replace("Z", "+00:00")).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if len(x) > 10 else x[:10] + "T00:00:00Z"
    except (ValueError, OverflowError, OSError):
        return None
    return None


def expiry_fields(d: Any, depth: int = 0) -> dict[str, str]:
    """{field name: ISO date} for every field whose NAME says expiry and whose value is a date. Names and dates only."""
    out: dict[str, str] = {}
    if isinstance(d, dict) and depth < 3:
        for k, v in d.items():
            if EXPIRY.search(str(k)) and _iso(v):
                out[str(k)] = _iso(v)
            elif isinstance(v, dict):
                out.update({f"{k}.{kk}": vv for kk, vv in expiry_fields(v, depth + 1).items()})
    return out


def finding(name: str, kind: str, state: str, why: str, path: str | None = None, expires_utc: str | None = None, fields: list[str] | None = None) -> dict[str, Any]:
    return {"name": name, "kind": kind, "state": state, "why": why, "path": path, "expires_utc": expires_utc, "fields_seen": fields}


def judge(name: str, kind: str, path: str | None, expiries: dict[str, str], now: dt.datetime, seen: list[str], what: str) -> dict[str, Any]:
    if not expiries:
        return finding(name, kind, "unreadable", f"{what} reports no expiry field (names seen: {', '.join(seen) or 'none'}); whether it has a lifetime is UNKNOWN", path, None, seen)
    first = min(expiries.values())
    left = (dt.datetime.fromisoformat(first.replace("Z", "+00:00")) - now).total_seconds()
    state = "expired" if left <= 0 else "expiring" if left < WARN_S else "ok"
    return finding(name, kind, state, f"{what}: {', '.join(sorted(expiries))} = {first}", path, first, seen)


def slot_user_findings(client: Any, slot_map: dict[str, dict], now: dt.datetime, probe: bool = False, secrets_dir: Path | None = None) -> list[dict[str, Any]]:
    from icsa.harness import slot_users as SU
    tok = client.admin_token(600)
    names, out, seen_all = {}, [], set()
    for key, v in sorted(slot_map.items()):
        n = key.rsplit("-", 1)
        if len(n) == 2 and n[1].isdigit():
            names[SU.slot_name(v["option"], int(n[1]))] = v["user"]
    me = client.oz("GET", "/user", tok).json()
    records = {"admin": me} | {name: client.oz("GET", f"/users/{uid}", tok, expect=None) for name, uid in names.items()}
    unreadable = []
    for name, rec in records.items():
        if name != "admin":
            if rec.status_code != 200:
                out.append(finding(name, "slot_user", "error", f"GET /users/<id> -> HTTP {rec.status_code}", None))
                continue
            rec = rec.json()
        seen_all |= set(rec) if isinstance(rec, dict) else set()
        ex = expiry_fields(rec)
        if ex:
            out.append(judge(name, "slot_user" if name != "admin" else "onezone_admin", None, ex, now, sorted(rec), "the Onezone user record"))
        else:
            unreadable.append(name)
    seen = sorted(seen_all)
    if unreadable:                     # one finding for all of them: the same record shape, the same answer
        out.append(finding("slot_users_password", "slot_user", "unreadable",
                           f"the Onezone user record of {len(unreadable)} of {len(records)} accounts (the slot users and the admin) has no field naming a password expiry (field names: {', '.join(seen)}); "
                           "whether Onezone gives a password a lifetime at all is UNKNOWN: ask the Onezone admin", None, None, seen))
    if probe:
        for name in names:
            try:
                SU.slot_user_token(client, name, [{"type": "time", "validUntil": int(now.timestamp()) + 60}], secrets_dir or SU.SECRETS_DIR)
                out.append(finding(name, "slot_user", "works", "its password opened the account just now (a token was minted and dropped); no lifetime is implied"))
            except SU.SlotUserError as e:
                out.append(finding(name, "slot_user", "rejected", re.sub(r"[^\w .:/()-]", "", str(e))[:120]))
    return out


def api_key_finding(name: str, key_file: str, probes: list[tuple[str, dict[str, str]]], session: Any, now: dt.datetime) -> dict[str, Any]:
    """`probes`: (url, headers) pairs to GET in turn, headers built here from the key's value, which is never kept past the call. The first non-404 answer's status decides
    works/rejected; expiry comes from any header or JSON field that names one."""
    p = Path(key_file).expanduser()
    if not p.is_file():
        return finding(name, "api_key", "error", "the key file is missing", str(p))
    mode = stat.S_IMODE(p.stat().st_mode)
    written = _iso(p.stat().st_mtime)
    expiries: dict[str, str] = {}
    statuses: list[str] = []
    rejected = False
    seen: set[str] = set()
    for i, (url, hdr) in enumerate(probes):
        try:
            r = session.get(url, headers=hdr(p.read_text().strip()), timeout=20)
        except Exception as e:  # noqa: BLE001 - the error class only, never its text (a URL or header could be in it)
            statuses.append(f"{url.split('/')[2]} {type(e).__name__}")
            continue
        statuses.append(f"{url.split('/')[2]}{url[url.index('/', 8):][:24]} HTTP {r.status_code}")
        rejected = rejected or (i == 0 and r.status_code in (401, 403))          # only the first, plain call decides; the others are guesses at where an expiry might be shown
        for hk, hv in (getattr(r, "headers", None) or {}).items():
            seen.add(str(hk).lower())
            if EXPIRY.search(str(hk)) and _iso(hv):
                expiries["header " + str(hk).lower()] = _iso(hv)
        try:
            body = r.json() if r.status_code == 200 else {}
        except Exception:  # noqa: BLE001
            body = {}
        expiries.update(expiry_fields(body.get("info", body) if isinstance(body, dict) else {}))
    base = f"key file mode {oct(mode)}, written {written}; asked: {'; '.join(statuses) or 'nothing'}"
    if rejected:
        return finding(name, "api_key", "rejected", base + "; the key is refused (HTTP 401/403)", str(p))
    f = judge(name, "api_key", str(p), expiries, now, sorted(h for h in seen if EXPIRY.search(h)), "the API's answer")
    f["why"] = f["why"] + f" ({base})"
    return f


def run(now: dt.datetime, *, onezone: bool = True, keys: bool = True, probe: bool = False, client: Any = None, session: Any = None, slot_map_path: Path | None = None,
        harness_cfg: Any = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if onezone:
        from icsa.faults.matcher import load_slot_map
        from icsa.harness import slot_users as SU
        from icsa.harness.slot_lease import SLOT_MAP
        sm = {k: {"option": s.option, "user": s.user} for k, s in load_slot_map(slot_map_path or SLOT_MAP).items()}
        try:
            out += slot_user_findings(client or SU.Client(), sm, now, probe)
        except Exception as e:  # noqa: BLE001 - Onezone unreachable or the admin file unreadable: said, never a value
            out.append(finding("slot_users_password", "slot_user", "error", f"Onezone could not be read: {type(e).__name__}"))
    if keys:
        import requests
        from icsa.harness.config import load_config
        hc = harness_cfg or load_config()
        s = session or requests.Session()
        ll = str(hc.site_b["base_url"]).rstrip("/")
        root = ll.rsplit("/api/v1", 1)[0] + "/api" if "/api/v1" in ll else ll
        out.append(api_key_finding("site_b_key", str(hc.site_b["key_file"]), [(ll + "/models", lambda k: {"Authorization": "Bearer " + k}),
                                                                           (root + "/key/info", lambda k: {"Authorization": "Bearer " + k})], s, now))
        out.append(api_key_finding("anthropic_key", str(hc.anthropic_key_file), [("https://host-10.invalid/v1/models", lambda k: {"x-api-key": k, "anthropic-version": "2023-06-01"})], s, now))
    return out


def write(root: Path, findings: list[dict[str, Any]], now: dt.datetime) -> Path:
    p = Path(root) / "credential_lifetimes.json"
    tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps({"checked_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "findings": findings}, indent=1))
    os.replace(tmp, p)
    return p


def read(root: Path) -> dict[str, Any] | None:
    """The last run's findings, or None (no run yet, or unreadable)."""
    try:
        d = json.loads((Path(root) / "credential_lifetimes.json").read_text())
        return d if isinstance(d, dict) and isinstance(d.get("findings"), list) else None
    except (OSError, ValueError):
        return None


def render(findings: list[dict[str, Any]]) -> str:
    return "\n".join(f"{f['state']:10} {f['kind']:13} {f['name']:22} {f['expires_utc'] or '-':21} {f['path'] or '-'}  {f['why']}" for f in findings)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="icsa.campaign.credlife", description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", required=True, help="the campaign dir: credential_lifetimes.json is written there")
    ap.add_argument("--probe-passwords", action="store_true", help="also show that each slot user's password opens its account now (mints and drops a 60 s token each)")
    ap.add_argument("--no-onezone", action="store_true")
    ap.add_argument("--no-keys", action="store_true")
    a = ap.parse_args(argv)
    now = dt.datetime.now(dt.timezone.utc)
    f = run(now, onezone=not a.no_onezone, keys=not a.no_keys, probe=a.probe_passwords)
    print(render(f))
    print(f"written: {write(Path(a.root), f, now)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
