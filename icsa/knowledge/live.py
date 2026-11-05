"""Live pieces for the knowledge plane (#6): the server's token and a probe of the real tools against the data provider.

    uv run python -m icsa.knowledge.live probe --space-id <id> --space-name <name> [--layout S1|S2]

Federation calls: run outside the sandbox. The token value is never printed."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from icsa.harness.config import load_config
from icsa.records import Layout

from . import equality, launch

from .tokencheck import MINT_TTL_S as TTL_S     # time cap + 1 h; mint a token per run


def mint_server_token(space_id: str, ttl_s: int = TTL_S) -> str:
    """The server's single token: read-only, REST-only, limited to the study space, short-lived (launch.scoped_caveats).
    Minted with the admin credentials but never admin-capable. The value is never printed."""
    sys.path.insert(0, os.environ.get("DAY0_SCRIPTS", str(Path(__file__).resolve().parents[2] / "day0" / "scripts")))
    import od  # noqa: E402
    import odpw  # noqa: E402,F401
    return od.mint_token(ttl_s, launch.scoped_caveats(space_id, ttl_s)[1:])   # mint_token adds the time caveat itself


def examine(token: str) -> dict:
    """Onezone's description of a token: id, subject, caveats (an admin-authenticated examine call)."""
    sys.path.insert(0, os.environ.get("DAY0_SCRIPTS", str(Path(__file__).resolve().parents[2] / "day0" / "scripts")))
    import od  # noqa: E402
    import odpw  # noqa: E402,F401
    return od.OD().oz("POST", "/tokens/examine", json={"token": token}).json()


def token_identity(token: str) -> dict:
    """What may be recorded about a token: its id, its subject (user) and its caveat types. Never the value."""
    j = examine(token)
    return {"token_id": j["id"], "subject": j.get("subject"), "persistence": j.get("persistence"),
            "caveats": [c["type"] for c in j.get("caveats", [])]}


def examine_caveats(token: str) -> list[dict]:
    """Ask Onezone for the caveats of a token (an admin-authenticated examine call), for the scope test."""
    sys.path.insert(0, os.environ.get("DAY0_SCRIPTS", str(Path(__file__).resolve().parents[2] / "day0" / "scripts")))
    import od  # noqa: E402
    import odpw  # noqa: E402,F401
    o = od.OD()
    j = o.oz("POST", "/tokens/examine", json={"token": token}).json()
    return j["caveats"] if "caveats" in j else j.get("token", {}).get("caveats", [])


async def probe(space_id: str, space_name: str, layout: Layout, insecure: bool = False) -> list[dict]:
    cfg = load_config()
    f = launch.knowledge_factory(cfg.knowledge, lambda: mint_server_token(space_id), space_id=space_id, insecure_tls=insecure)
    out = []
    async with f() as kp:
        for tool, args in equality.probes(space_name, layout):
            text, err = await kp.call(tool, args)
            out.append({"tool": tool, "args": args, "is_error": err, "text": text[:1500]})
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["probe"])
    ap.add_argument("--space-id", required=True)
    ap.add_argument("--space-name", required=True)
    ap.add_argument("--layout", default="S1")
    ap.add_argument("--insecure-tls", action="store_true")
    a = ap.parse_args()
    for r in asyncio.run(probe(a.space_id, a.space_name, Layout(a.layout), a.insecure_tls)):
        print(json.dumps(r, ensure_ascii=False)[:1800])
