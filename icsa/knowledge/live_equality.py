"""Run the knowledge-plane equality check (#6) on the real sandboxes and the real data provider.

    uv run python -m icsa.knowledge.live_equality --out results/knowledge

Needs docker + sudo (the sandboxes) and the Onedata admin secret; run outside the Bash sandbox. Per layout it starts T,
T-unpaginated, D and M (campaign_data_config, oneclient --insecure) plus one control run of T. Tokens: the sandboxes
get read-only, space-scoped tokens (REST for T/T-unpaginated/D, oneclient for M); the knowledge plane gets its OWN
read-only, space-scoped token, minted once and the same in every option. No admin token reaches any of them."""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
import time
from pathlib import Path

from icsa.harness.config import Limits as RunLimits, load_config
from icsa.records import Layout, Option
from icsa.sandbox import Limits, Sandbox, SandboxConfig, campaign_data_config
from icsa.sandbox.config import pin_image

from . import equality, launch, live, pin, tokencheck

SPACE_ID = "30f507e9ae7b06e4b0af93fb125b8a92chb984"
SPACE_NAME = "icsa2027_data_20261101T090944Z"
PROVIDER_HOST = "host-12.invalid"
ONEZONE = "host-9.invalid"
S1_BYTES, S2_BYTES = 4254680853, 3785412176          # du -sb of s1z / s2z (#3)


def sandbox_token(interface: str, ttl_s: int = tokencheck.MINT_TTL_S) -> str:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "day0" / "scripts"))
    import od  # noqa: E402
    import odpw  # noqa: E402,F401
    cav = [{"type": "data.readonly"}, {"type": "interface", "interface": interface},
           {"type": "data.path", "whitelist": [base64.b64encode(f"/{SPACE_ID}".encode()).decode()]}]
    return od.mint_token(ttl_s, cav)


def main() -> int:
    from icsa.sandbox.termination import exit_on_sigterm
    exit_on_sigterm()     # a SIGTERM is an orderly exit: the sandboxes are stopped in order
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--layouts", default="S1,S2")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    pin.verify_pin()
    cfg = load_config()
    plane_ids: list[dict] = []
    run_token_ids: list[str] = []

    def plane_token() -> str:           # one fresh token per plane start, as a run does; each has its own id
        tok = live.mint_server_token(SPACE_ID)
        idn = live.token_identity(tok)
        tokencheck.assert_distinct(idn["token_id"], run_token_ids)
        plane_ids.append(idn)
        return tok

    factory = launch.knowledge_factory(cfg.knowledge, plane_token, space_id=SPACE_ID)
    IMAGE = "icsa-sandbox:1"
    sbx_cfg = SandboxConfig(image=IMAGE, pinned_image_id=pin_image(IMAGE), limits=Limits.for_dataset(S1_BYTES, S2_BYTES, memory_bytes=8 * 1024 ** 3))   # a check, not a study run: explicit limit

    def checked_sandbox_token(interface: str) -> str:
        tok = sandbox_token(interface)
        # the sandbox/oneclient tokens are read-only and space-scoped too; Onezone says so before they are used
        info = tokencheck.require_scoped_token(tok, SPACE_ID)
        run_token_ids.append(info["token_id"])
        tokencheck.assert_distinct_all([p["token_id"] for p in plane_ids], run_token_ids)
        return tok

    def data_config_for(opt: Option):
        kw = dict(onezone_host=ONEZONE, space_name=SPACE_NAME, provider_hosts=[PROVIDER_HOST], s1_path="s1z",
                  s2_path="s2z/sst_s2.nc")
        if opt is Option.M:
            kw.update(oneclient_token=checked_sandbox_token("oneclient"), oneclient_provider_host=PROVIDER_HOST)
        else:
            kw.update(token=checked_sandbox_token("rest"))
        return campaign_data_config(**kw)

    def sandbox_factory(run_key, option, layout, data_config):
        return Sandbox.start(run_key, option, layout, data_config, sbx_cfg)

    limits = RunLimits(max_tool_rounds=10, time_cap_s=600, token_budget=1000, output_cap_chars=cfg.limits.output_cap_chars,
                       max_output_tokens=100)
    ok = True
    for lay in a.layouts.split(","):
        layout = Layout(lay)
        r = asyncio.run(equality.run_check(layout, SPACE_NAME, sandbox_factory, factory, data_config_for, limits,
                                           a.out / f"equality_{lay}.json"))
        r["plane_principal"] = plane_ids[-1]
        r["plane_token_ids"] = [p["token_id"] for p in plane_ids]
        r["user_agent"] = pin.user_agent()
        r["launcher"] = "icsa/knowledge/serve.py (not the stock onedata-mcp entrypoint): only httpx's default User-Agent is set"
        r["run_token_ids"] = list(run_token_ids)
        r["plane_token_check"] = "tokencheck.require_scoped_token passed at every plane start"
        (a.out / f"equality_{lay}.json").write_text(json.dumps(r, indent=1, ensure_ascii=False, default=str) + "\n")
        print(lay, "identical:", r["identical"], "differences:", len(r["differences"]), "volatile:", r["volatile_probes_in_control"])
        ok &= r["identical"]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
