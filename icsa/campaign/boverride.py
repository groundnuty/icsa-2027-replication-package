"""B's provider override: one extra dispatcher per new Onedata provider, each on its own host and seeing ONE provider (#34).

The campaign's dispatcher reads site_g: its provider host, space and ids are module constants of files the snapshot's code walk covers
(`snapshot/codecheck.py`, `icsa.instruments.validate.code_files`), and those files must stay byte-identical to main's. So B does not edit them. This module
(imported by `icsa/campaign/cli.py`, by tests, and by the interpreter's start-up file below, so outside the walk) replaces the constants in memory, from a
`b_provider` block of the launch JSON:

    "b_provider": {"name": "site_u", "host": "host-8.invalid", "addr": "198.51.100.5", "port": 30451, "provider_id": "...", "space_id": "...",
                   "space_name": "...", "slot_prefix": "icsa2027-slot-w0-", "slot_map_file": "/abs/slot_map.json", "plan_file": "/abs/plan.json",
                   ["lease_dir": "/abs/dir", "secrets_dir": "/abs/dir", "insecure_tls": true, "waive_level_memory": false,
                    "sonnet_release_gate": false, "waive_read_check": false,
                    "service_user": "user_33", "service_pass_file": "/abs/service.pass"]}

`host` is the provider's DOMAIN as Onezone registers it (the name the sandboxes, the gate and oneclient know; `precheck` refuses a launch whose host differs from it);
`addr` is where the gate and the host connect when the name is no address (omitted: `host`); `port` is the provider's NodePort. The Onezone is the one the code has
(host-9.invalid): every provider is registered in it.

With no block nothing here runs and nothing is replaced: `load_config` is `CampaignConfig.from_json` and the rest of the command is as it was.

EVERY PYTHON PROCESS OF B. A B dispatcher starts children that import site_g's constants afresh: the live check's probe (`python -m icsa.scripted live-probe`, which builds its
data target from `federation.MAIN` and leases slot users from the slot map), the read check's bench, the site_g-settings command. A child of the dispatcher inherits its
environment, so the override is installed at interpreter start, in B's own virtualenv, by a `.pth` file that lives outside the repository (so the code stamp and the walk
never see it): `python -m icsa.campaign.boverride write-pth` writes it into the running interpreter's site-packages, and it does nothing unless `ICSA_B_PROVIDER` names the
launch file (or a file holding the block). An override that fails to install in a child ENDS that process (exit 87): a child that read site_g by mistake would measure site_g.
`install` is idempotent for the same block, so the dispatcher's own install in cli.py and the one at its start are one.

What `install` replaces (tests/campaign/test_boverride.py checks each site, and builds the real objects with fakes to read the values they carry):

  by name, in the module that owns it      real_sandbox, oracle_real, slot_users (and its change log and slot map defaults), slot_lease, knowledge.launch,
                                           knowledge.live_equality, scripted.federation (MAIN)
  by value, in a module that imported it   health (the host the check reads, the study space, the supporter's id), oracle_real
  default arguments bound at def time      slot_users.token_caveats and mint_run_token (space_id), slot_lease.SlotPool.__init__ and pool_status (slot map, lease dir); each
                                           by parameter NAME, and only when it holds the value it should
  keyword defaults                         health.health_check (post, get), knowledge.launch.server_environment (insecure_tls)
  the route, in sandbox.route              configured_provider_port (B's NodePort: the gate's upstream, oneclient's -P, the knowledge server's URL, frprobe's port) and
                                           apply_provider_route (the gate's upstream entry for the provider, and the gate's TLS mode)
  optional (`waive_level_memory`)          livecheck.read_memory: the rise rule's op_worker memory input is waived (science, 4 Nov 15:07Z), recorded as waived in the inputs
  optional (`secrets_dir`)                 slot_users.SECRETS_DIR and the def-time defaults that carry it: B's slot users' passwords, read and written there
  optional (`service_user`)                real_sandbox.mint_token, health.mint_token, knowledge.tokencheck.default_examine, knowledge.live.examine: the knowledge plane's
                                           token, the health check's token and Onezone's examination of a token are made as a read-only SERVICE USER of B's space,
                                           so the Onezone admin's password is not on the B host (the admin file is read nowhere on B's run path)
  optional (`waive_read_check`)            frprobe.check_configured: the scripted commands' own pre-block read check (`baseline` refuses unless it is ok, whatever the dispatcher's
                                           `read_check_required` says; its reference is site_g's rate) reports a waiver as `ok`, saying so
  optional (`sonnet_release_gate`)         gate.evaluate: B's Sonnet main runs wait for the release file alone (main's gate prices from the store's own runs, which a B store never has)

TLS (the new providers have self-signed certificates). oneclient is `--insecure` for the whole campaign already. The harness's own REST calls (the health check) are verified
or not by HOST: `verify=False` only for the B provider's address, Onezone stays verified. Two switches are global in the code they reach, and the override sets them for B,
and says so in its start line: the gate's `verify_ssl` (one flag for every upstream of one gate, Onezone included) and the knowledge server's ONEDATA_ALLOW_INSECURE_TLS.

A dispatcher that runs models on another host (`hosts` in the launch file) is refused: the remote runner would execute runs without this override.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from .config import CampaignConfig

BLOCK = "b_provider"
ENV = "ICSA_B_PROVIDER"
EXIT_REFUSED = 5
EXIT_CHILD_NOT_INSTALLED = 87
PTH_NAME = "zz_icsa_b_override.pth"

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_HOST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$")        # a name or a dotted address: no scheme, no port, no path
_ID = re.compile(r"^[A-Za-z0-9]{8,80}$")
_SPACE_NAME = re.compile(r"^icsa2027_data_[0-9A-Za-z]{1,32}$")
_SERVICE_USER = re.compile(r"^icsa2027-slot-[a-z0-9]+-svc-\d+$")          # B's read-only service user: a slot-user name of the option "svc", which no run ever leases (Onezone refuses a "+" in a name)
RUN_OPTIONS = ("T", "T-unpaginated", "D", "M")
_PREFIX = re.compile(r"^icsa2027-slot-[a-z0-9]+-$")               # B's slot users: icsa2027-slot-<tag>-<option>-<n>, never site_g's icsa2027-slot-<option>-<n>
_KEYS_REQUIRED = ("name", "host", "port", "provider_id", "space_id", "space_name", "slot_prefix", "slot_map_file", "plan_file")
_KEYS_OPTIONAL = ("addr", "lease_dir", "insecure_tls", "waive_level_memory", "sonnet_release_gate", "waive_read_check", "service_user", "service_pass_file", "secrets_dir")
WAIVER = "waived for B (science, #34, 4 Nov 15:07Z): op_worker's memory input to the rise rule is not read"


class BOverrideError(ValueError):
    """A b_provider block or plan that cannot be used: nothing is installed, nothing runs."""


@dataclasses.dataclass(frozen=True)
class BProvider:
    name: str                     # a label for the record
    host: str                     # the provider's domain as Onezone has it: the name the sandboxes, the gate and oneclient know (a DNS name, or an address)
    port: int                     # the provider's NodePort: the one route (what [network] provider_port is for site_g)
    provider_id: str
    space_id: str
    space_name: str
    slot_prefix: str
    slot_map_file: str
    plan_file: str
    addr: str = ""                # where the gate and the host connect, when `host` is no address; default `host`
    lease_dir: str | None = None
    insecure_tls: bool = True
    waive_level_memory: bool = False
    sonnet_release_gate: bool = False
    waive_read_check: bool = False
    secrets_dir: str | None = None    # where this B's slot users' (and the service user's) password files are: the default of every slot_users reader and writer
    service_user: str = ""        # a read-only member of B's space only, whose password file (`service_pass_file`) stands in for the Onezone ADMIN's on the B host: see `_service_mint`
    service_pass_file: str = ""

    @property
    def connect(self) -> str:
        return self.addr or self.host

    @property
    def authority(self) -> str:
        """`host:port` as a URL has it, for the harness's own REST calls (which build `https://{host}/...` with no port, i.e. 443)."""
        return f"{self.connect}:{self.port}"


def _outside_hashed_tree(path: str, what: str) -> None:
    from icsa import codestamp
    hit = codestamp.hashed_root_of(path, Path(__file__).resolve().parents[2])
    if hit:
        raise BOverrideError(f"{BLOCK}.{what} {path} sits inside {hit}/, which the code hash covers: keep it outside the tree")


def parse_block(raw: Any) -> BProvider:
    """The validated block; every property B depends on is checked here, before anything is replaced."""
    if not isinstance(raw, dict):
        raise BOverrideError(f"{BLOCK} must be an object")
    unknown = sorted(set(raw) - set(_KEYS_REQUIRED) - set(_KEYS_OPTIONAL))
    missing = [k for k in _KEYS_REQUIRED if k not in raw]
    if unknown or missing:
        raise BOverrideError(f"{BLOCK}: unknown keys {unknown}, missing keys {missing}")

    def text(key: str, rx: re.Pattern) -> str:
        v = raw.get(key)
        if not isinstance(v, str) or not rx.fullmatch(v):
            raise BOverrideError(f"{BLOCK}.{key} is not valid: {v!r}")
        return v
    port = raw["port"]
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise BOverrideError(f"{BLOCK}.port must be an integer in 1..65535, got {port!r}")
    flags = {}
    for key, default in (("insecure_tls", True), ("waive_level_memory", False), ("sonnet_release_gate", False), ("waive_read_check", False)):
        flags[key] = raw.get(key, default)
        if not isinstance(flags[key], bool):
            raise BOverrideError(f"{BLOCK}.{key} must be true or false, got {flags[key]!r}")
    if ("service_user" in raw) != ("service_pass_file" in raw):
        raise BOverrideError(f"{BLOCK}: service_user and service_pass_file go together")
    paths = {}
    for key in ("slot_map_file", "plan_file", "lease_dir", "service_pass_file", "secrets_dir"):
        v = raw.get(key)
        if v is None and key in ("lease_dir", "service_pass_file", "secrets_dir"):
            continue
        if not isinstance(v, str) or not v or not Path(v).is_absolute():
            raise BOverrideError(f"{BLOCK}.{key} must be an absolute path, got {v!r}")
        _outside_hashed_tree(v, key)
        paths[key] = v
    if re.fullmatch(r"[0-9.]+", str(raw.get("host"))):
        raise BOverrideError(f"{BLOCK}.host {raw['host']!r} is an address: the gate intercepts a provider by NAME (--add-host, the run's CA), so use the provider's domain as Onezone "
                             "registers it and put the address in `addr`")
    return BProvider(name=text("name", _NAME), host=text("host", _HOST), port=port, provider_id=text("provider_id", _ID), space_id=text("space_id", _ID),
                     space_name=text("space_name", _SPACE_NAME), slot_prefix=text("slot_prefix", _PREFIX),
                     slot_map_file=paths["slot_map_file"], plan_file=paths["plan_file"], lease_dir=paths.get("lease_dir"), secrets_dir=paths.get("secrets_dir"),
                     addr=text("addr", _HOST) if "addr" in raw else "", service_user=text("service_user", _SERVICE_USER) if "service_user" in raw else "",
                     service_pass_file=paths.get("service_pass_file", ""), **flags)


def load_config(path: str | Path | None) -> tuple[CampaignConfig, BProvider | None]:
    """`(CampaignConfig.from_json(path), None)` when the launch file has no block: that one call and nothing else, exactly what the commands did before. With a block, the block
    is validated and taken out first, because `from_json` refuses a key it does not know (it is the first such key it meets that it names)."""
    if path is None:
        return CampaignConfig.from_json(None), None
    try:
        return CampaignConfig.from_json(path), None
    except KeyError as e:
        if e.args != (f"unknown campaign config key: {BLOCK}",):
            raise
    raw = json.loads(Path(path).read_text())
    block = parse_block(raw.pop(BLOCK))
    with tempfile.TemporaryDirectory(prefix="b-launch-") as d:
        stripped = Path(d) / "launch.json"
        stripped.write_text(json.dumps(raw))
        return CampaignConfig.from_json(stripped), block


def block_from_file(path: str | Path) -> BProvider:
    """The block of a launch file, or of a file that holds the block alone."""
    try:
        raw = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise BOverrideError(f"{ENV} names {path}, which cannot be read as JSON: {type(e).__name__}: {e}") from None
    return parse_block(raw[BLOCK] if isinstance(raw, dict) and BLOCK in raw else raw)


# ---- the plan: which runs this dispatcher's store holds -----------------------------------------------------------------------------------------

def load_plan(path: str | Path) -> list[str]:
    try:
        keys = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise BOverrideError(f"{BLOCK}.plan_file {path} cannot be read: {type(e).__name__}: {e}") from None
    if not isinstance(keys, list) or not keys or not all(isinstance(k, str) and k for k in keys):
        raise BOverrideError(f"{BLOCK}.plan_file {path} must be a non-empty JSON list of run keys")
    dup = sorted({k for k in keys if keys.count(k) > 1})
    if dup:
        raise BOverrideError(f"{BLOCK}.plan_file names a run key more than once: {dup[:5]}")
    return keys


def filter_rows(rows: list, plan_file: str | Path) -> list:
    """The manifest rows of the plan only, each unchanged (run key, seed, seq, group, stage) and in the manifest's own order. A key the manifest does not have is refused: a plan
    that silently shrinks would run fewer runs than the lead asked for."""
    keys = load_plan(plan_file)
    have = {r.run_key for r in rows}
    unknown = [k for k in keys if k not in have]
    if unknown:
        raise BOverrideError(f"{BLOCK}.plan_file names {len(unknown)} run key(s) the manifest does not have, e.g. {unknown[:5]}")
    keep = set(keys)
    return [r for r in rows if r.run_key in keep]


# ---- the replacement ----------------------------------------------------------------------------------------------------------------------------

_ACTIVE: list[Callable[[], None]] | None = None
_BLOCK: BProvider | None = None
_ENV_BLOCK: BProvider | None = None       # the block this process installed at its start, from ICSA_B_PROVIDER (the .pth): proof that this interpreter's venv has the start-up file


def installed() -> bool:
    return _ACTIVE is not None


def installed_block() -> BProvider | None:
    return _BLOCK


def env_block() -> BProvider | None:
    """The block the interpreter's start-up file installed from ICSA_B_PROVIDER, None when this process was not started so."""
    return _ENV_BLOCK


def uninstall() -> None:
    """Put every replaced value back (tests; a dispatcher exits instead)."""
    global _ACTIVE, _BLOCK, _ENV_BLOCK
    undo, _ACTIVE, _BLOCK, _ENV_BLOCK = _ACTIVE, None, None, None
    for f in reversed(undo or []):
        f()


def install(b: BProvider, cfg: Any = None, *, err=None, setup: bool = False) -> None:
    """Replace site_g's constants with B's, process-wide. The same block again is a no-op; another block is refused. Refuses a block that carries site_g's own values, a slot map that
    shares a user with site_g's, and a launch with more than one run host. Everything is checked before the first value is replaced. `setup` (only the `slot-users` command passes it) excuses
    a slot map that does not exist yet, which `slot_users apply` is about to write; nothing that runs, probes or starts a child can: no environment variable gives it."""
    global _ACTIVE, _BLOCK
    from .hosts import multi_host
    if cfg is not None and multi_host(cfg):
        raise BOverrideError("a B launch runs on one host: `hosts` in the launch file would send runs to a remote runner that has no override")
    if _ACTIVE is not None:
        if _BLOCK == b:
            return
        raise BOverrideError(f"an override is already installed in this process, for {_BLOCK.name} (a launch file whose {BLOCK} differs from {ENV}?), not {b.name}")
    from icsa import frprobe
    from icsa.campaign import gate as GATE, livecheck as LC
    from icsa.knowledge import live as KLIVE, tokencheck as TC
    from icsa.harness import health as H, oracle_real as OR, real_sandbox as RS, slot_lease as SL, slot_users as SU
    from icsa.knowledge import launch as KL, live_equality as LE
    from icsa.sandbox import route as R
    from icsa.scripted import federation as F

    site_g = {"host": RS.PROVIDER_HOST, "space_id": RS.SPACE_ID, "provider_id": H.SITE_G_PROVIDER_ID}
    for what, mine in (("host", b.host), ("host", b.connect), ("space_id", b.space_id), ("provider_id", b.provider_id)):
        if mine == site_g[what]:
            raise BOverrideError(f"{BLOCK}.{what} is site_g's own ({mine}): B reads a provider of its own")
    if b.slot_prefix == SU.PREFIX:
        raise BOverrideError(f"{BLOCK}.slot_prefix is site_g's slot users' prefix")
    from icsa.faults.matcher import load_slot_map
    try:
        mine_users = set() if (setup and not Path(b.slot_map_file).exists()) else {s.user for s in load_slot_map(Path(b.slot_map_file)).values()}
        site_g_users = {s.user for s in load_slot_map(SL.SLOT_MAP).values()}
    except (OSError, ValueError) as e:
        raise BOverrideError(f"{BLOCK}.slot_map_file {b.slot_map_file} or the tree's own slot map cannot be read: {type(e).__name__}: {e}") from None
    try:
        odd = sorted({s.option for s in load_slot_map(Path(b.slot_map_file)).values()} - set(RUN_OPTIONS)) if Path(b.slot_map_file).exists() else []
    except (OSError, ValueError):
        odd = []
    if odd:
        raise BOverrideError(f"{BLOCK}.slot_map_file names slot users of option(s) {odd}: only {list(RUN_OPTIONS)} are run options (the service user has a map of its own)")
    if mine_users & site_g_users:
        raise BOverrideError(f"{BLOCK}.slot_map_file names slot users of site_g's map: {sorted(mine_users & site_g_users)[:3]}")

    undo: list[Callable[[], None]] = []

    def put(obj: Any, name: str, value: Any) -> None:
        old = getattr(obj, name)
        setattr(obj, name, value)
        undo.append(lambda: setattr(obj, name, old))

    def put_default(fn: Callable, param: str, expect: Any, value: Any) -> None:
        """The positional default of parameter `param` of `fn`, bound at def time, replaced BY NAME; it must hold `expect` (a changed signature or a value already replaced is not
        skipped silently, and two parameters that happen to hold the same value are not mixed up)."""
        old = fn.__defaults__ or ()
        code = fn.__code__
        names = code.co_varnames[:code.co_argcount][code.co_argcount - len(old):]
        if param not in names or old[names.index(param)] != expect:
            raise BOverrideError(f"{fn.__qualname__}'s default of {param!r} is not {expect!r}: the code changed under the override")
        i = names.index(param)
        fn.__defaults__ = old[:i] + (value,) + old[i + 1:]
        undo.append(lambda: setattr(fn, "__defaults__", old))

    def put_kwdefault(fn: Callable, key: str, value: Any) -> None:
        old = dict(fn.__kwdefaults__ or {})
        if key not in old:
            raise BOverrideError(f"{fn.__qualname__} has no keyword default {key!r}: the code changed under the override")
        fn.__kwdefaults__ = {**old, key: value}
        undo.append(lambda: setattr(fn, "__kwdefaults__", old))

    try:
        # 1. real_sandbox (the one place the real sandbox is configured) and oracle_real, which imported its names by value. The Onezone is the same for every provider.
        for mod in (RS, OR):
            put(mod, "PROVIDER_HOST", b.host)
            put(mod, "SPACE_NAME", b.space_name)
            put(mod, "SPACE_ID", b.space_id)
        # 2. the health check: by-value names, the supporter it expects, and its REST calls (verify off for B's address only)
        put(H, "PROVIDER_HOST", b.authority)            # the check builds https://{PROVIDER_HOST}/api/..., with no port of its own
        put(H, "SPACE_ID", b.space_id)
        put(H, "SPACE_NAME", b.space_name)
        put(H, "SITE_G_PROVIDER_ID", b.provider_id)
        if b.insecure_tls:
            put_kwdefault(H.health_check, "post", _host_scoped("post", b.authority))
            put_kwdefault(H.health_check, "get", _host_scoped("get", b.authority))
        # 3. the slot users: the study space (global and default), the prefix and the pattern that must accept it
        put(SU, "STUDY_SPACE_ID", b.space_id)
        put(SU, "STUDY_SPACE_NAME", b.space_name)
        put(SU, "PREFIX", b.slot_prefix)
        put(SU, "_NAME", re.compile(rf"^{re.escape(b.slot_prefix)}(T|T-unpaginated|D|M|M\+|svc)-(\d+)$"))
        put(SU, "wanted", _wanted_with_service(SU.wanted))
        put_default(SU.token_caveats, "space_id", site_g["space_id"], b.space_id)
        put_default(SU.mint_run_token, "space_id", site_g["space_id"], b.space_id)
        # B's slot users are made by slot_users' own `plan` and `apply` under this override: their defaults for the change log and the slot map would be site_g's (the tree's
        # config/slot_map.json, which `apply` rewrites), so they are B's files, beside the slot map the block names
        if b.secrets_dir:                 # the slot users' passwords: where the tokens are minted from, and where `apply` writes them (every default bound at def time, by name)
            site_g_secrets = SU.SECRETS_DIR
            put(SU, "SECRETS_DIR", Path(b.secrets_dir))
            for fn, param in ((SU.read_slot_password, "dirpath"), (SU.slot_user_token, "dirpath"), (SU.mint_run_token, "dirpath"), (SU.apply, "secrets_dir"),
                              (SU.teardown, "secrets_dir")):
                put_default(fn, param, site_g_secrets, Path(b.secrets_dir))
        put(SU, "DEFAULT_MAP", Path(b.slot_map_file))
        put(SU, "DEFAULT_LOG", Path(b.slot_map_file).with_suffix(".changes.jsonl"))
        # 4. the slot pool: B's own users (its map), and its own lease directory when it names one
        site_g_map, site_g_leases = SL.SLOT_MAP, SL.LEASE_DIR            # read before they are replaced: they are the defaults bound into the two functions
        put(SL, "SLOT_MAP", Path(b.slot_map_file))
        put_default(SL.SlotPool.__init__, "slot_map_path", site_g_map, Path(b.slot_map_file))
        put_default(SL.pool_status, "slot_map_path", site_g_map, Path(b.slot_map_file))
        if b.lease_dir:
            put(SL, "LEASE_DIR", Path(b.lease_dir))
            put_default(SL.SlotPool.__init__, "lease_dir", site_g_leases, Path(b.lease_dir))
            put_default(SL.pool_status, "lease_dir", site_g_leases, Path(b.lease_dir))
        # 5. the knowledge plane: the server's provider (the address the host reaches), its TLS switch, the check script's names
        put(KL, "DATA_PROVIDER_NAME", b.connect)
        if b.insecure_tls:
            put_kwdefault(KL.server_environment, "insecure_tls", True)
        put(LE, "SPACE_ID", b.space_id)
        put(LE, "SPACE_NAME", b.space_name)
        put(LE, "PROVIDER_HOST", b.connect)
        # 6. the scripted data target (the live check's probes)
        put(F, "MAIN", dataclasses.replace(F.MAIN, space_name=b.space_name, space_id=b.space_id, provider=b.name, provider_host=b.host))
        # 7. the route: B's NodePort, and the gate's upstream for the provider
        put(R, "configured_provider_port", lambda: R.validate_port(b.port))
        put(R, "apply_provider_route", _b_route(R.apply_provider_route, b))
        # 8. the rise rule's memory input, when science waived it for B
        if b.waive_level_memory:
            put(LC, "read_memory", _waived_memory)
        # 8b. no admin credential on the host: the tokens and the examination as the service user
        if b.service_user:
            put(RS, "mint_token", _service_mint(RS.mint_token, b))
            put(H, "mint_token", RS.mint_token)
            examine = _service_examine(b)
            put(TC, "default_examine", examine)
            put(KLIVE, "examine", examine)
        # 8c. the read check, waived (science, 4 Nov 15:07Z) for the scripted commands too
        if b.waive_read_check:
            put(frprobe, "check_configured", _waived_read_check(b))
        # 9. the Sonnet gate: held until a release file
        if b.sonnet_release_gate:
            put(GATE, "evaluate", _release_gate_evaluate)
    except BaseException:
        for f in reversed(undo):
            f()
        raise
    _ACTIVE, _BLOCK = undo, b
    print(f"b_override: {b.name} {b.host} (connects to {b.authority}) space {b.space_id}, slot users {b.slot_prefix}*, "
          f"{'TLS verification OFF for the gate and the knowledge server (single global switches), for the harness REST calls to this address only' if b.insecure_tls else 'TLS verified'}"
          f"{'; op_worker memory waived in the rise rule' if b.waive_level_memory else ''}"
          f"{'; Sonnet main runs held until the release file' if b.sonnet_release_gate else ''}"
          f"{'; the pre-block read check waived' if b.waive_read_check else ''}"
          f"{'; tokens and examination as the service user ' + b.service_user + ' (no admin password read)' if b.service_user else ''}", file=err or sys.stderr)


def _host_scoped(method: str, authority: str) -> Callable:
    """`requests.<method>` that verifies nothing for the B provider's address, and everything for any other host (Onezone). Resolved at call time."""
    def call(url: str, *a: Any, **kw: Any):
        import requests
        if urlsplit(url).netloc == authority:
            kw["verify"] = False
        return getattr(requests, method)(url, *a, **kw)
    call.__name__ = f"{method}_b_scoped"
    return call


def _waived_read_check(b: BProvider) -> Callable:
    """`frprobe.check_configured` for a B launch that waives the read check: `ok`, with the waiver as the reason, no rate and no threshold, so no record can read it as a measurement."""
    def check_configured(*, timeout_s: float = 180.0, run: Callable | None = None) -> dict[str, Any]:
        return {"state": "ok", "mbit_s": None, "ref_mbit_s": None, "threshold_mbit_s": None, "port": b.port, "why": f"waived for B (science, #34, 4 Nov 15:07Z): no read was made, {b.name}'s rate is not known"}
    return check_configured


def _waived_memory(path, field, time_field, id_field, t0, t1, gap_s, max_bytes=8 << 20):
    """`livecheck.read_memory` for a B launch that waives the input: a known reading of no change, and it says so, so the rise rule's record shows a waiver and not a measurement."""
    return {"field": field, "start": 0.0, "end": 0.0, "pct": 0.0, "readings": 0, "median_of": 0, "waived": WAIVER}, ""


def _wanted_with_service(orig: Callable) -> Callable:
    """`slot_users.wanted` that also takes the option "svc": the read-only service user (`icsa2027-slot-<tag>-svc-1`), made by `apply --options svc --per-option 1 --map <its own map>`.
    It is not an option of any run, so no slot map of B may name it (install refuses one that does) and no run can lease it."""
    def wanted(options=SU_OPTIONS, per_option: int = 1):
        options = tuple(options)
        svc = [o for o in options if o == "svc"]
        out = orig(tuple(o for o in options if o != "svc"), per_option) if len(svc) != len(options) else []
        from icsa.harness import slot_users as SU
        return [*out, *[SU.Slot("svc", n) for _ in svc for n in range(1, per_option + 1)]]
    return wanted


SU_OPTIONS = ("T", "T-unpaginated", "D", "M")           # slot_users.OPTIONS, which `wanted` takes as its default


def _service_auth(b: BProvider) -> dict[str, str]:
    """The service user's basic-auth header, read at use time from its password file; the value is never printed or kept."""
    import base64
    try:
        pw = Path(b.service_pass_file).read_text().strip()
    except OSError as e:
        raise RuntimeError(f"the service user's password file {b.service_pass_file} cannot be read ({type(e).__name__})") from None
    if not pw:
        raise RuntimeError(f"the service user's password file {b.service_pass_file} is empty")
    return {"authorization": "Basic " + base64.b64encode(f"{b.service_user}:{pw}".encode()).decode()}


def _service_mint(orig: Callable, b: BProvider) -> Callable:
    """`real_sandbox.mint_token` (the knowledge plane's token and the health check's: the services' principal) with the service user in place of the admin: the same caveats, the
    same lifetime rule, the same record, minted by the one POST of the original, whose basic-auth header is replaced by the service user's. Its `pass_file` is the service user's."""
    def mint(*, oneclient: bool, time_cap_s: float, ttl_s: int | None = None, post: Callable | None = None, pass_file: Any = None, interface: str | None = None,
             service: bool = False):
        def post_as_service(url: str, **kw: Any):
            import requests
            kw["headers"] = {**(kw.get("headers") or {}), **_service_auth(b)}
            return (post or requests.post)(url, **kw)
        return orig(oneclient=oneclient, time_cap_s=time_cap_s, ttl_s=ttl_s, post=post_as_service, pass_file=pass_file if pass_file is not None else Path(b.service_pass_file),
                    interface=interface, service=service)
    return mint


def _service_examine(b: BProvider) -> Callable:
    """Onezone's description of a token (id, subject, caveats), asked as the service user: what the knowledge plane's scope test (`tokencheck.require_scoped_token`) reads."""
    def examine(token: str) -> dict:
        import requests
        from icsa.harness import real_sandbox as RS
        r = requests.post(f"https://{RS.ONEZONE_HOST}/api/v3/onezone/tokens/examine", json={"token": token}, headers=_service_auth(b), timeout=30)
        if r.status_code >= 300:
            raise RuntimeError(f"token examination as the service user failed: HTTP {r.status_code}")
        return r.json()
    return examine


GATE_SINCE = "b_gate_since"


def _release_gate_evaluate(store: Any, cfg: Any, keys: Any = None, latch: bool = True) -> dict[str, Any]:
    """`gate.evaluate` for a B store. Main's gate prices Sonnet from the store's own priced runs (6 Sonnet calibration runs and 50 Haiku main runs) and holds every Sonnet seed
    until they exist (`hold_unpriced`), a state that no release file ends: a B store has no calibration block and cannot reach it. The lead's word for B is main's gate having
    released (its projection covers all of seed 1, B's runs included), so B's gate is the release file alone: Sonnet's main-block runs of every seed wait (`hold_after_seed` 0)
    until the file `gate_release_file` exists and was written AFTER this store's first evaluation (the rule of gate.py: a file older than the decision it releases does not
    count; the time is kept in the store, so a restart keeps it). Haiku and the open models are never held (the scheduler holds only `gate_model`'s runs). With no gate model
    this is as main's: off. The state shows as `hold_unknown`, the one main's gate uses for a hold that a release lifts, and `proceed` after it."""
    import datetime as dt
    from . import release
    sm = cfg.gate_model
    out: dict[str, Any] = {"model": sm, "max_usd": cfg.gate_max_usd, "release_file": cfg.gate_release_file, "released": False, "released_by": None,
                           "projected_usd": None, "state": "off", "held": False}
    if not sm or sm not in cfg.api_models:
        return out
    since = store.get_meta(GATE_SINCE)
    if since is None and latch:
        since = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        store.put_meta(GATE_SINCE, since, since)
        store.event(since, "sonnet_gate", sm, "B's Sonnet gate is the release file alone: Sonnet main runs wait for a file written after this moment, at "
                    f"{cfg.gate_release_file} (main's pricing needs calibration runs that a B store does not have)")
    released_by = release.written_after(cfg.gate_release_file, release.epoch_of(since)) if (since and cfg.gate_release_file) else None
    out.update(released=bool(released_by), released_by=released_by, decided_utc=since, authorised_seed=None,
               state="proceed" if released_by else "hold_unknown", held=not released_by, hold_after_seed=None if released_by else 0,
               why=[] if released_by else ["B's gate is the release file alone: " + (f"no file at {cfg.gate_release_file} written after {since}" if since else "not yet evaluated by the dispatcher")])
    return out


def _b_route(orig: Callable, b: BProvider) -> Callable:
    def apply_provider_route(kw: dict, *, via: str | None = None) -> dict:
        if via is not None:
            raise ValueError(f"B has one route, its provider's port {b.port}: via={via!r} (Traefik) is site_g's fault calibration")
        kw = dict(kw)
        up = dict(kw.get("upstream") or {})
        if b.connect != b.host:        # the gate connects to the address; the sandboxes know the name
            up.setdefault(b.host, {"addr": b.connect, "port": b.port, "tls": True})
            if kw.get("oneclient_provider_host") == b.host:
                kw["oneclient_provider_host"] = b.connect
        kw["upstream"] = up
        if b.insecure_tls:
            kw["verify_ssl"] = False
        return orig(kw, via=None)
    return apply_provider_route


# ---- the precheck: the provider is the one the block says ---------------------------------------------------------------------------------------

_PYTHON = re.compile(r"python(3(\.\d+)?)?")
_FLAG_VALUE = ("-W", "-X", "-Q")           # python options that take the next word as their value


def python_invocation(cmd: Any) -> tuple[list[str], list[str], str | None, str | None] | None:
    """`cmd` as a Python launch: (argv up to and including the interpreter, the interpreter's own flags, the kind of its operand, the operand), None when it names no interpreter.
    `env A=B /path/.venv/bin/python -u -m icsa.scripted live-probe` gives (`env A=B /path/.venv/bin/python`, `-u`, "m", `icsa.scripted`); a script gives ("script", its path),
    `-c` ("c", the code), none (None, None) when python is given no operand (a REPL, or standard input)."""
    if not isinstance(cmd, (list, tuple)):
        return None
    words = [str(x) for x in cmd]
    for i, a in enumerate(words):
        if _PYTHON.fullmatch(Path(a).name):
            break
    else:
        return None
    flags: list[str] = []
    k = i + 1
    while k < len(words) and words[k].startswith("-") and words[k] != "-":
        w = words[k]
        if w in ("-m", "-c"):
            return words[:i + 1], flags, w[1:], words[k + 1] if k + 1 < len(words) else None
        flags.append(w)
        k += 1
        if w in _FLAG_VALUE and k < len(words):
            flags.append(words[k])
            k += 1
    return words[:i + 1], flags, ("script" if k < len(words) else None), (words[k] if k < len(words) else None)


def disables_site(flags: list[str]) -> bool:
    """A short-option cluster with S (`-S`, `-IS`): the interpreter skips `site`, which is where `.pth` files are read, so the override is not installed in it."""
    return any(f.startswith("-") and not f.startswith("--") and "S" in f[1:] and f not in _FLAG_VALUE for f in flags)


STDLIB_ONLY_TOOLS = ("/tools/provider_watch/cat_fresh.py",)      # scripts that read nothing of the harness: no override, and no check of their interpreter


_PROBE_CODE = ("import json; import icsa.harness.real_sandbox as R, icsa.scripted.federation as F, icsa.harness.slot_lease as S; "
               "print(json.dumps({'host': R.PROVIDER_HOST, 'space_id': R.SPACE_ID, 'main': F.MAIN.space_id, 'slot_map': str(S.SLOT_MAP)}))")


def interpreter_problems(b: BProvider, cfg: Any, run: Callable | None = None) -> list[str]:
    """Every Python command of the launch file (the live check's probes; any other command that starts one) is run with the dispatcher's own environment, the command's own
    interpreter flags, and asked what provider it would read: it must say B's. A command built on another virtualenv (main's, with the `.pth` missing or a tree that has no
    override: exit 87) reads site_g, and a probe that reads site_g judges B's load by site_g's, so the launch does not start. An interpreter started with `-S` skips the `.pth`: refused. A
    script on the stdlib-only list is exempt when it IS the script the command runs (the operand), not when its name appears anywhere in the command."""
    import subprocess
    run = run or subprocess.run
    cmds = []
    for shape, cmd in sorted((getattr(cfg, "live_check_cmds", None) or {}).items()):
        cmds.append((f"live_check_cmds[{shape}]", cmd))
    for key in ("site_g_settings_cmd", "site_g_disk_cmd", "log_check_cmd", "fincore_cmd"):
        if getattr(cfg, key, None):
            cmds.append((key, getattr(cfg, key)))
    out: list[str] = []
    for label, cmd in cmds:
        inv = python_invocation(cmd)
        if inv is None:
            continue                                # not a Python command (ssh, kubectl): it reads nothing of the harness's constants
        pre, flags, kind, operand = inv
        if kind == "script" and operand and str(Path(operand)).endswith(STDLIB_ONLY_TOOLS):
            continue                                # a stdlib-only tool: it reads nothing of the harness's constants
        if disables_site(flags):
            out.append(f"{label}: its interpreter ({' '.join(pre[-2:])} {' '.join(flags)}) is started with -S, which skips the .pth: the override would not be installed in it")
            continue
        try:
            p = run([*pre, *flags, "-c", _PROBE_CODE], capture_output=True, text=True, timeout=180, env=dict(os.environ))
        except Exception as e:  # noqa: BLE001 -- a check that cannot run is a failed check
            out.append(f"{label}: its interpreter could not be asked what it reads ({type(e).__name__}: {str(e)[:120]})")
            continue
        try:
            got = json.loads(p.stdout.strip().splitlines()[-1]) if p.returncode == 0 and p.stdout.strip() else None
        except ValueError:
            got = None
        if got is None:
            out.append(f"{label}: its interpreter ({' '.join(pre[-3:])}) exited {p.returncode} when asked what it reads: {p.stderr.strip()[-300:]}")
        elif (got.get("host"), got.get("space_id"), got.get("main"), got.get("slot_map")) != (b.host, b.space_id, b.space_id, b.slot_map_file):
            out.append(f"{label}: its interpreter ({' '.join(pre[-3:])}) would read host {got.get('host')!r}, space {got.get('space_id')!r}, slot map {got.get('slot_map')!r}, not B's: "
                       f"it has no {PTH_NAME} (run `python -m icsa.campaign.boverride write-pth` with that venv's python) or does not inherit {ENV}")
    return out


def precheck(b: BProvider, cfg: Any = None, *, post: Callable | None = None, get: Callable | None = None, mint: Callable | None = None,
             run: Callable | None = None) -> list[str]:
    """Why this launch must not start, [] when it may. Run after `install`, before the first run, on the dispatcher's host (network: Onezone, the provider).
    Onezone's view is the authority: the study space exists under the configured name, is supported by the configured provider and no other, and that provider's registered
    DOMAIN is the configured `host` (the sandboxes reach the provider by that name; a provider registered by another name serves the gate's certificate to nobody). The
    provider's own /configuration is read too: its providerId must be the configured one, and its domain, when it states one, the configured host. A check that cannot be
    made is a problem, never a pass. With the launch config (`cfg`), the interpreter of every Python command in it must read B's provider too (`interpreter_problems`)."""
    from icsa.harness import real_sandbox as RS
    problems: list[str] = []
    try:
        import requests
        post, get, mint = post or requests.post, get or requests.get, mint or RS.mint_token
        tok = mint(oneclient=False, time_cap_s=300.0, service=True)[0]
        r = post(f"https://{RS.ONEZONE_HOST}/api/v3/onezone/tokens/infer_access_token_scope", json={"token": tok}, timeout=30)
        if r.status_code != 200:
            return [f"Onezone's scope inference answered HTTP {r.status_code}: the provider's registered domain cannot be read"]
        scope = r.json()["dataAccessScope"]
        sp = (scope.get("spaces") or {}).get(b.space_id)
        if not sp or sp.get("name") != b.space_name:
            problems.append(f"space {b.space_id} named {b.space_name} is not in the token's scope in Onezone")
        elif sorted(sp.get("supports", [])) != [b.provider_id]:
            problems.append(f"the space is supported by {sorted(sp.get('supports', []))}, expected only {b.provider_id}")
        prov = (scope.get("providers") or {}).get(b.provider_id)
        if not prov:
            problems.append(f"provider {b.provider_id} is not in the token's scope in Onezone")
        elif prov.get("domain") != b.host:
            problems.append(f"Onezone registers provider {b.provider_id} as {prov.get('domain')!r}, the launch says {b.host!r}: the gate and the sandboxes would name another host")
        conf = get(f"https://{b.authority}/api/v3/oneprovider/configuration", timeout=30, **({"verify": False} if b.insecure_tls else {}))
        if conf.status_code != 200:
            problems.append(f"the provider's /configuration at {b.authority} answered HTTP {conf.status_code}")
        else:
            js = conf.json()
            if js.get("providerId") != b.provider_id:
                problems.append(f"the provider at {b.authority} says it is {js.get('providerId')!r}, the launch says {b.provider_id!r}")
            if "domain" in js and js["domain"] != b.host:
                problems.append(f"the provider at {b.authority} says its domain is {js['domain']!r}, the launch says {b.host!r}")
            if "onezoneDomain" in js and js["onezoneDomain"] != RS.ONEZONE_HOST:
                problems.append(f"the provider at {b.authority} belongs to the Onezone {js['onezoneDomain']!r}, not {RS.ONEZONE_HOST!r}")
    except Exception as e:  # noqa: BLE001 -- a check that cannot run is a failed check
        problems.append(f"the provider could not be checked: {type(e).__name__}: {str(e)[:200]}")
    if b.service_user:
        problems += _service_problems(b, post, mint)
    if cfg is not None:
        problems += interpreter_problems(b, cfg, run)
    return problems


def _service_problems(b: BProvider, post: Callable | None, mint: Callable | None) -> list[str]:
    """What the knowledge plane does with the service user, once, as it will per run: mint the server's token (REST only, read-only, B's space) and have Onezone examine it
    as the same user; the examination must show the scope the plane requires. Whether Onezone lets a non-admin examine a token is NOT known: this is the probe."""
    from icsa.harness import real_sandbox as RS
    from icsa.harness.config import load_config
    from icsa.knowledge import tokencheck
    try:
        cap = load_config().limits.time_cap_s
        tok = (mint or RS.mint_token)(oneclient=False, interface="rest", time_cap_s=cap, ttl_s=tokencheck.ttl_window(cap)[2])[0]
        tokencheck.require_scoped_token(tok, b.space_id, time_cap_s=cap)
    except Exception as e:  # noqa: BLE001 -- a check that cannot run is a failed check
        return [f"the service user {b.service_user} cannot do what the knowledge plane needs of it (mint a read-only REST token of B's space and have it examined): {type(e).__name__}: {str(e)[:200]}"]
    return []


# ---- every Python process of B ------------------------------------------------------------------------------------------------------------------

def install_from_env() -> None:
    """For the interpreter's start (the `.pth`): install the block `ICSA_B_PROVIDER` names; nothing when it is unset."""
    global _ENV_BLOCK
    path = os.environ.get(ENV)
    if path:
        b = block_from_file(path)
        install(b)
        _ENV_BLOCK = b


_PTH_CODE = ("import os\n"
             "try:\n"
             " import icsa.campaign.boverride as _b\n"
             " _b.install_from_env()\n"
             "except BaseException as _e:\n"
             " try:\n"
             "  os.write(2, ('b_override: NOT INSTALLED in a process of a B launch (%s names the block), so it would read site_g: %r\\n' % (os.environ.get('" + ENV + "'), _e)).encode())\n"
             " except BaseException:\n"
             "  pass\n"
             " os._exit(" + str(EXIT_CHILD_NOT_INSTALLED) + ")\n")
PTH_LINE = f"import os; os.environ.get({ENV!r}) and exec({_PTH_CODE!r})"


def write_pth(directory: str | Path | None = None) -> Path:
    """The `.pth` file, in `directory` (default: the running interpreter's own site-packages: run it with B's virtualenv's python)."""
    import sysconfig
    d = Path(directory) if directory else Path(sysconfig.get_paths()["purelib"])
    p = d / PTH_NAME
    p.write_text(PTH_LINE + "\n")
    return p


def slot_plan(b: BProvider, rows: list, cap: int, venv_python: str = ".venv/bin/python") -> dict[str, Any]:
    """How many slot users B's store needs per option, and the commands that create them (the lead runs them; the admin password is on that host only). A run holds one user of
    its option for its whole life, so an option needs as many users as it can have runs at once: at most `cap` (the host's sandbox cap) and at most its runs in the plan. The live
    check's probe holds a T and an M user of its own, kept out of the run pool (`live_check_slot_keys`), and the check needs BOTH shapes (`livecheck.config_problems`), so T and M
    are always made, with the probe's user, whether or not the plan has a run of that option. `slot_users apply` makes the same number for every option it is given and writes the
    map of what it made, so ONE call with the highest number, for the options below."""
    from collections import Counter
    counts = Counter(r.run.option.value for r in rows)
    options = [o for o in ("T", "T-unpaginated", "D", "M") if counts.get(o) or o in ("T", "M")]
    needed = {o: min(cap, counts.get(o, 0)) + (1 if o in ("T", "M") else 0) for o in options}
    n = max(needed.values())
    probes = {o: f"{o}-{n}" for o in ("T", "M")}
    run_cmd = f"{venv_python} -m icsa.campaign.boverride slot-users --config <launch file>"      # NOT `-m icsa.harness.slot_users`: that re-runs the module as __main__, with site_g's constants
    return {"provider": b.name, "plan_runs": len(rows), "runs_by_option": dict(counts), "cap": cap, "users_needed_by_option": needed, "per_option": n,
            "slot_keys": {o: [f"{o}-{i}" for i in range(1, n + 1)] for o in options}, "live_check_slot_keys": probes,
            "run_pool_keys": {o: [f"{o}-{i}" for i in range(1, n + 1) if probes.get(o) != f"{o}-{i}"] for o in options},
            "service_user": b.service_user or f"{b.slot_prefix}svc-1",
            "commands": [f"{run_cmd} plan --options {' '.join(options)} --per-option {n}",
                         f"{run_cmd} apply --options {' '.join(options)} --per-option {n} --map {b.slot_map_file} --yes",
                         f"{run_cmd} apply --options svc --per-option 1 --map <the service user's map file> --yes"],
            "notes": [f"run them WITHOUT {ENV} set: the command installs the override itself, and takes the slot map as not yet existing",
                      f"the passwords go to the block's secrets_dir ({b.secrets_dir or 'the host default'}), the change log beside the slot map; copy both to the B host"]}


def freeze(cfg: Any, *, yes: bool) -> dict[str, Any]:
    """The two files a B launch needs before its first start and that nothing else can write for B's host label (`opw-restart` takes only site_g and site_f): the frozen settings hash
    (`site_g_settings_frozen_file`, the canonical hash of what the launch's settings command prints NOW) and the restart log's baseline for `site_g_restart_host` (the pod's identity now).
    Both are written once, at the freeze: an existing frozen hash that differs, or a baseline already in the log, is never changed (that is a decision, not this command's). Without
    `yes` it only reads and says what it would write."""
    from icsa import frsettings, opwrestart
    try:
        fields = frsettings.read_fields(cfg.site_g_settings_cmd, cfg.site_g_settings_timeout_s) if cfg.site_g_settings_cmd else None
    except ValueError as e:
        raise BOverrideError(f"the settings command cannot be read: {e}") from None
    if fields is None:
        raise BOverrideError("the launch has no site_g_settings_cmd")
    h, ident = frsettings.canonical_hash(fields), opwrestart.identity(fields)
    if not opwrestart.has_process_start(ident):
        raise BOverrideError(f"the settings carry no readable op_worker process start ({ident}): a restart inside the pod could not show, so no baseline is written")
    frozen, host, log = Path(cfg.site_g_settings_frozen_file), cfg.site_g_restart_host, cfg.site_g_restart_log
    if frozen.exists():
        try:
            have = frsettings.read_frozen(frozen)
        except ValueError as e:
            raise BOverrideError(f"{frozen} exists and is not a hash: {e}") from None
        if have != h:
            raise BOverrideError(f"{frozen} holds {have}, the provider shows {h}: the settings changed since the freeze; moving it is a decision, not this command's")
    try:
        entries = opwrestart.read_log(log) if Path(log).exists() else []
    except ValueError as e:
        raise BOverrideError(f"the restart log {log} cannot be used: {e}") from None
    mine = [e for e in entries if e["host"] == host]
    if mine and not any(e["kind"] == "baseline" for e in mine):
        raise BOverrideError(f"the restart log holds entries for {host} but no baseline: it is not a fresh log; not touched")
    out = {"host": host, "hash": h, "identity": ident, "frozen_file": str(frozen), "frozen_exists": frozen.exists(), "restart_log": str(log),
           "baseline_exists": bool(mine), "written": []}
    if yes:
        if not frozen.exists():
            frozen.parent.mkdir(parents=True, exist_ok=True)
            frozen.write_text(h + "\n")
            out["written"].append(str(frozen))
        if not mine:
            opwrestart.append(log, {"kind": "baseline", "host": host, "identity": ident, "hash": h, "reason": "B's freeze (boverride freeze)"})
            out["written"].append(str(log))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="icsa.campaign.boverride", description="B's provider override: the interpreter's start-up file, and the provider precheck")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write-pth", help=f"write {PTH_NAME} into this interpreter's site-packages (or --dir): it installs the override in every process that has {ENV} set")
    w.add_argument("--dir")
    c = sub.add_parser("precheck", help="read Onezone and the provider and say whether the launch's provider is the one it names (needs the network and the admin password)")
    c.add_argument("--config", required=True, help="the launch file (or a file holding the block)")
    su = sub.add_parser("slot-users", help="icsa.harness.slot_users (plan, apply, teardown) with B's override installed: B's space, prefix, passwords and files; the slot map need not exist yet")
    su.add_argument("--config", required=True, help="the launch file (or a file holding the block)")
    su.add_argument("rest", nargs=argparse.REMAINDER, help="what slot_users takes: plan|apply|teardown [--options ..] [--per-option N] [--map F] [--yes]")
    fz = sub.add_parser("freeze", help="write the frozen settings hash and the restart-log baseline for this launch's provider, from what its settings command prints now (once; --yes writes)")
    fz.add_argument("--config", required=True, help="the launch file")
    fz.add_argument("--yes", action="store_true")
    sp = sub.add_parser("slots", help="how many slot users B's store needs per option for its plan, and the commands that create them (reads the manifest, no network)")
    sp.add_argument("--config", required=True, help="the launch file")
    sp.add_argument("--cap", type=int, help="the host's sandbox cap (default: the launch file's max_sandboxes)")
    sp.add_argument("--venv-python", default=".venv/bin/python")
    a = ap.parse_args(argv)
    if a.cmd == "freeze":
        import icsa.campaign.boverride as me
        try:
            cfg, b = me.load_config(a.config)
            print(json.dumps(me.freeze(cfg, yes=a.yes), indent=1))
        except me.BOverrideError as e:
            print(e, file=sys.stderr)
            return EXIT_REFUSED
        return 0
    if a.cmd == "slot-users":
        import icsa.campaign.boverride as me          # the importable module's state, not this `__main__`'s
        try:
            me.install(me.block_from_file(a.config), setup=True)
        except me.BOverrideError as e:
            print(e, file=sys.stderr)
            return EXIT_REFUSED
        from icsa.harness import slot_users          # the instance the override patched: never `-m icsa.harness.slot_users`, which runs a second copy as __main__ with site_g's values
        return slot_users.main(a.rest)
    if a.cmd == "slots":
        from .manifest import build_manifest
        from icsa.instances.load import load_all_instances
        try:
            cfg, b = load_config(a.config)
            if b is None:
                raise BOverrideError(f"{a.config} has no {BLOCK} block")
            rows = filter_rows(build_manifest(cfg, load_all_instances()), b.plan_file)
        except BOverrideError as e:
            print(e, file=sys.stderr)
            return EXIT_REFUSED
        cap = a.cap or cfg.max_sandboxes
        if not cap or cap < 1:
            print("give --cap (the host's sandbox cap) or set max_sandboxes in the launch file", file=sys.stderr)
            return EXIT_REFUSED
        print(json.dumps(slot_plan(b, rows, cap, a.venv_python), indent=1))
        return 0
    if a.cmd == "write-pth":
        print(write_pth(a.dir))
        return 0
    import icsa.campaign.boverride as me          # run as `-m`, this file is `__main__`: the state that the start-up file's install keeps is the importable module's
    try:
        b = me.block_from_file(a.config)
        me.install(b)
    except me.BOverrideError as e:
        print(e, file=sys.stderr)
        return EXIT_REFUSED
    try:
        cfg = me.load_config(a.config)[0] if me.BLOCK in json.loads(Path(a.config).read_text()) else None
    except (OSError, ValueError, KeyError):
        cfg = None
    problems = me.precheck(b, cfg)
    print(json.dumps({"provider": b.name, "host": b.host, "port": b.port, "ok": not problems, "problems": problems}))
    return 0 if not problems else EXIT_REFUSED


if __name__ == "__main__":
    sys.exit(main())
