"""Campaign configuration (#16).

Every value here is a default that a JSON file can override (`--config`).
Items marked PLACEHOLDER wait on the science agent's `protocol/` or on #1.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
from pathlib import Path
from typing import Any

from icsa.records import Layout, Option

PILOT_MODEL = "Qwen3.8-27B"
# Reporting name -> endpoint key (the `model` field of ~/icsa-paths/endpoints.json).
# The run record keeps the reporting name (RunId.model) and the API id (model_api_id).
OPEN_MODELS = {
    "Qwen3.8-27B": "qwen",
    "Qwen3-Coder-30B-A3B": "qwencoder",
    "DeepSeek-V4-Flash-0731": "deepseek",
    "GLM-5.3-Flash": "glm",
    "Gemma-4-31B": "gemma",
}
MODEL_API_IDS = {
    "Qwen3.8-27B": "Qwen/Qwen3.8-27B",
    "Qwen3-Coder-30B-A3B": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
    "DeepSeek-V4-Flash-0731": "deepseek-ai/DeepSeek-V4-Flash-0731",
    "GLM-5.3-Flash": "zai-org/GLM-5.3-Flash",
    "Gemma-4-31B": "google/gemma-4-31B",
    "claude-haiku-5-5": "claude-haiku-5-5",
    "claude-sonnet-5-5": "claude-sonnet-5-5",
}
CLAUDE_MODELS = ("claude-haiku-5-5", "claude-sonnet-5-5")
ALL_MODELS = tuple(OPEN_MODELS) + CLAUDE_MODELS
# S2 priority tiers (protocol c44c52a): A runs before B
TIER_A = ("Qwen3.8-27B", "claude-haiku-5-5", "claude-sonnet-5-5")
TIER_B = ("Gemma-4-31B", "GLM-5.3-Flash", "DeepSeek-V4-Flash-0731", "Qwen3-Coder-30B-A3B")


def _anthropic_caps_from_harness() -> dict[str, int]:
    from icsa.harness.config import load_config
    return {k.split(":", 1)[1]: int(v) for k, v in load_config().provider_concurrency.items() if k.startswith("anthropic:")}


def group_of(block: str, layout: str, model: str) -> str:
    """The priority group of a run (BlockSpec.interleave), derived from the run's own fields (#34).
    The runs table does not store it. Mirrors default_blocks(); a custom block list that changes the
    groups needs its own mapping."""
    if block == "pagination" or (block == "main" and layout == "S1"):
        return "main_s1"
    if block == "main" and layout == "S2":
        return "main_s2_a" if model in TIER_A else "main_s2_b"
    if block == "calibration":
        return "pilot1"
    if block == "pilot":
        return "pilot"
    return block


# Amendments 27(b) and 29(b), seed-first: the order is in stages for each seed (block 1, then S2 tier A, then S2 tier B), and nothing in a real launch
# chooses another. A stage is named by its seed and its priority group.
def stage_label(group: str, seed: int) -> str:
    """The stage of a run under seed-first: its priority group within its seed. The group alone names it under the registered order."""
    return f"seed{seed}:{group}"


def _zoned(x: str) -> dt.datetime:
    t = dt.datetime.fromisoformat(x.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError(f"{x!r} has no time zone")
    return t


@dataclasses.dataclass
class BlockSpec:
    """A block is the product options x layouts x models x instances x seeds."""

    name: str
    options: list[str]
    layouts: list[str]
    models: list[str]
    seeds: list[int]
    instances: str = "all"        # "all" | "pilot" (the Instance.pilot subset)
    enabled: bool = True
    interleave: str = "main"      # priority group: blocks with the same name are shuffled together and
                                  # groups run in order of first appearance; "after" = own group, last
    exclude_from_analysis: bool = False  # #14 drops these rows; carried to every run record

    def option_enums(self) -> list[Option]:
        return [Option(o) for o in self.options]

    def layout_enums(self) -> list[Layout]:
        return [Layout(x) for x in self.layouts]


def default_blocks() -> list[BlockSpec]:
    return [
        # pilot 30 = 1 model x {T, D, M} x S1 x 10 pilot instances x seed 1 (issue #2)
        BlockSpec("pilot", ["T", "D", "M"], ["S1"], [PILOT_MODEL], [1], "pilot", True, "pilot"),
        # calibration 42 = 7 models x {T, D, M} x {S1, S2} x 1 pilot instance x seed 1, after the pilot
        # and before main; used only to set the caps, so every analysis excludes it.
        # Provisional caps (150 tool calls, 4M tokens, 240 min) come from protocol-draft.
        BlockSpec("calibration", ["T", "D", "M"], ["S1", "S2"], list(ALL_MODELS), [1], "pilot1", True,
                  "calibration", exclude_from_analysis=True),
        # main 6,300 = 3 x 2 x 7 x 50 x 3, in priority groups (protocol c44c52a):
        #   main_s1 (protected, never dropped): all S1 runs + the pagination cell, shuffled together;
        #   main_s2_a: S2 for tier A; main_s2_b: S2 for tier B. Both carry block "main".
        BlockSpec("main", ["T", "D", "M"], ["S1"], list(ALL_MODELS), [1, 2, 3], "all", True, "main_s1"),
        # pagination 350 = T-unpaginated x S1 x 7 x 50 (one seed)
        BlockSpec("pagination", ["T-unpaginated"], ["S1"], list(ALL_MODELS), [1], "all", True, "main_s1"),
        BlockSpec("main", ["T", "D", "M"], ["S2"], list(TIER_A), [1, 2, 3], "all", True, "main_s2_a"),
        BlockSpec("main", ["T", "D", "M"], ["S2"], list(TIER_B), [1, 2, 3], "all", True, "main_s2_b"),
        # Optional 300-run blocks, disabled until the science agent enables them.
        # PLACEHOLDER composition (2 options x 1 model x 50 instances x 3 seeds = 300):
        # issue #2 only says "a second implementation (T, M) and a second-harness check".
        BlockSpec("optional_second_impl", ["T", "M"], ["S1"], [PILOT_MODEL], [1, 2, 3], "all", False, "after"),
        BlockSpec("optional_second_harness", ["T", "M"], ["S1"], [PILOT_MODEL], [1, 2, 3], "all", False, "after"),
    ]


@dataclasses.dataclass
class Price:
    """USD per million tokens. None = not verified (PLACEHOLDER): USD shows n/a."""

    input_per_mtok: float | None = None
    output_per_mtok: float | None = None
    source: str = "UNVERIFIED placeholder: set from the Anthropic price list and cite the URL and date"
    # Prompt caching. input_per_mtok prices only the uncached remainder of the prompt. None = the
    # standard multipliers of the price list: cache read 0.1 x input, 1-hour cache write 2 x input.
    cache_read_per_mtok: float | None = None
    cache_write_1h_per_mtok: float | None = None
    # A long-prompt tier (Haiku 5.5): a REQUEST whose prompt is longer than `long_above_tokens` is billed at the `long_*`
    # rates (None = the same multipliers of long_input_per_mtok). The store keeps only per-attempt sums, so unless the
    # caller can show that every call of an attempt stayed at or under the threshold, the whole attempt is priced at the
    # long rates: an upper bound, never an underestimate. None = no such tier.
    long_above_tokens: int | None = None
    long_input_per_mtok: float | None = None
    long_output_per_mtok: float | None = None
    long_cache_read_per_mtok: float | None = None
    long_cache_write_1h_per_mtok: float | None = None


# Campaign prices, USD per million tokens. Source: the claude-api skill's pricing reference (models table cached
# 2026-10-06, "Prompt Caching" economics), read 1 Nov 2026; Anthropic first-party API rates.
#   Sonnet 5.5  $2 in / $10 out, cache read $0.20 (the skill states it), 1-hour write 2 x input = $4.
#   Haiku 5.5   $0.10 in / $0.50 out up to 100K prompt tokens, $0.50 / $2.50 above that (skill: "$0.50 / $2.50 beyond").
#               The skill gives no Haiku cache rates: read 0.1 x and 1-hour write 2 x of the tier's input rate
#               (its stated multipliers: "Cache reads cost ~0.1x base input ... 1-hour TTL 2x").
#   Opus 5.5    $4 in / $20 out, cache read $0.20 (0.05 x, the skill states it), 1-hour write 2 x input = $8.
#               Opus 5.5 is not a campaign model; the #76 inspection coders use it and the spend alarm prices them here.
# The harness sets cache_control ttl "1h" (icsa/harness/adapters.py), so cache writes are the 1-hour rate.
PRICE_SOURCE = ("claude-api skill pricing reference (models table cached 2026-10-06; prompt-caching economics), "
                "read 1 Nov 2026; Anthropic first-party API rates")
CAMPAIGN_PRICES: dict[str, Price] = {
    "claude-sonnet-5-5": Price(2.0, 10.0, PRICE_SOURCE, cache_read_per_mtok=0.20, cache_write_1h_per_mtok=4.0),
    "claude-haiku-5-5": Price(0.10, 0.50, PRICE_SOURCE, cache_read_per_mtok=0.01, cache_write_1h_per_mtok=0.20,
                              long_above_tokens=100_000, long_input_per_mtok=0.50, long_output_per_mtok=2.50,
                              long_cache_read_per_mtok=0.05, long_cache_write_1h_per_mtok=1.00),
    "claude-opus-5-5": Price(4.0, 20.0, PRICE_SOURCE, cache_read_per_mtok=0.20, cache_write_1h_per_mtok=8.0),
}
CODER_MODEL = "claude-opus-5-5"
# site_g's memory alarm (science, #34, 23:57Z): "hard stops at op_worker over 50% of the node or the node over 80%... keep the same absolute limits as a campaign alarm". Both are
# shares of the node's memory, read from the monitor (the same 50 and 80 as its own rule), so they hold when site_g's memory changes. An alarm only: nothing in the scheduler reads them.
SITE_G_MEM_OPW_MAX_PCT = 50.0
SITE_G_MEM_NODE_MAX_PCT = 80.0
SITE_G_MEM_MAX_AGE_S = 300.0              # a reading older than this is unknown (the coordinator, 3 Nov); it must exceed the interval of the copy to this host
SITE_G_MEM_GROWTH_WINDOW_H = 6.0          # op_worker's growth per hour is fitted over this window...
SITE_G_MEM_GROWTH_MIN_SPAN_H = 3.0        # ...and is null until the samples in it cover at least this long


def default_prices() -> dict[str, Price]:
    return {m: dataclasses.replace(p) for m, p in CAMPAIGN_PRICES.items()}


@dataclasses.dataclass
class CampaignConfig:
    rng_seed: int = 20271104
    blocks: list[BlockSpec] = dataclasses.field(default_factory=default_blocks)
    # Past the pilot only when the science agent has said go (issue #2: go/no-go).
    past_pilot: bool = False
    max_attempts: int = 3
    # Priority between groups (they are priorities, not barriers; pilot and calibration stay hard barriers):
    #  "per_model" (default): a run of model X starts only if X has no earlier-group run left to dispatch
    #     (pending and not in flight); other models are independent, so a free endpoint is never idle
    #     because another model still has earlier work.
    #  "strict": a run starts only if no run of an earlier group is pending anywhere (in flight counts).
    priority_mode: str = "per_model"
    # Global cap on concurrent runs (agent sandboxes, the data provider): the scarce resource. None = only
    # the per-provider caps apply. Each free sandbox goes to the first dispatchable run in manifest
    # (= priority) order across all models.
    max_sandboxes: int | None = None
    # The concurrency cap per priority group (BlockSpec.interleave: main_s1 = block 1 = main S1 + pagination, main_s2_a, main_s2_b), each set
    # from that group's own cells (science, #12, 1 Nov). A group absent here falls back to `max_sandboxes`; the pilot and calibration
    # groups ("pilot", and calibration's rows, whose group is "calibration") run at the cap of main_s1 when it is set (the registered text says the pilot
    # runs at the cap); in one cap, they and block 1 count every sandbox in flight, whichever block it belongs to.
    max_sandboxes_by_block: dict[str, int] = dataclasses.field(default_factory=dict)
    # no run of a later block starts while a run of one of these blocks is still pending
    barrier_blocks: list[str] = dataclasses.field(default_factory=lambda: ["pilot", "calibration"])
    # The blocks among `barrier_blocks` that run TOGETHER (amendment 29(g), replacing the barrier between pilot and calibration): their agent runs are
    # dispatched at once under the caps, each still holds back every later block until none of its runs is pending, and before the go (`past_pilot` false)
    # they are all candidates, so calibration no longer waits for the go. Blocks of `barrier_blocks` not listed here run one after the other, as before; [] =
    # the old order. `barrier_blocks` itself stays the membership that the Sonnet gate and the slot margin read.
    concurrent_barrier_blocks: list[str] = dataclasses.field(default_factory=lambda: ["pilot", "calibration"])
    # What OTHER processes hold beside this campaign while they run (amendment 29(g): fault calibration and the direct-path validation set run alongside the
    # pilot and calibration, "counted in the caps"; the lead, 3 Nov). {name: {"sandboxes": n, "slot_keys": [...]}}, for the names in
    # icsa/harness/reservation.py (PROCESS_OPTIONS), e.g. {"fault_calibration": {"sandboxes": 1, "slot_keys": [<the top .23 key of each option>]},
    # "validation_set": {"sandboxes": 1, "slot_keys": [...]}}. While a process's lock in `reservation_dir` (or ICSA_RESERVATION_DIR) is held, its `sandboxes` count in
    # every cap and in the local host's own cap, and its `slot_keys` are out of the campaign's local pool; a lock that cannot be read counts as held, and alarms.
    # The process takes its lock for as long as it runs, so its death frees the reservation. Launch config, outside the hashed tree; {} = none.
    reservation_dir: str = ""
    process_reservations: dict[str, dict] = dataclasses.field(default_factory=dict)
    # models -> endpoint key in endpoints.json; Claude models go to the API.
    open_models: dict[str, str] = dataclasses.field(default_factory=lambda: dict(OPEN_MODELS))
    api_models: list[str] = dataclasses.field(default_factory=lambda: list(CLAUDE_MODELS))
    # concurrency cap per provider (PLACEHOLDER values: set after the pilot, #8)
    provider_of: dict[str, str] = dataclasses.field(default_factory=dict)  # model -> provider; default below
    provider_caps: dict[str, int] = dataclasses.field(default_factory=lambda: {"site_a": 4, "anthropic": 4})
    default_cap: int = 1
    # Claude caps are PER MODEL (science, #34: the measured clean levels, Sonnet 8 and Haiku 16), like site_b_caps. The
    # one source is config/harness.toml [scheduler.provider_concurrency] ("anthropic:<model>" keys); a Claude model
    # with no entry falls back to provider_caps["anthropic"].
    anthropic_caps: dict[str, int] = dataclasses.field(default_factory=lambda: _anthropic_caps_from_harness())
    # Sessions one site_a SLOT can hold at once, by endpoint key (measured, #34 capacity report; Coder's 3 is an estimate). The
    # scheduler never puts more than this many runs on one slot, whatever the provider cap says. A key with no entry: no per-slot cap.
    site_a_slot_caps: dict[str, int] = dataclasses.field(default_factory=lambda: {
        "qwen": 16, "deepseek": 4, "glm": 4, "gemma": 2, "qwencoder": 3})
    # site_g's settings hash (science, #2, 2 Nov 03:54Z; icsa/frsettings.py): a command printing Traefik's and op_worker's image and args as
    # JSON, hashed and compared with the frozen value in `site_g_settings_frozen_file`. Mismatch stops dispatch, unknown holds it.
    # On unless set off: required with no command is unknown, which holds dispatch. So a launch cannot skip it by leaving it out; a host without site_g, and a
    # test, sets `site_g_settings_required` false, and the event log says so. It also governs the disk check below.
    site_g_settings_cmd: list[str] | None = None
    site_g_settings_frozen_file: str = "/mnt/volume2/icsa-2027/site_g_settings.frozen"
    site_g_settings_required: bool = True
    # The op_worker restart log (icsa/opwrestart.py; science, #34, 3 Nov 00:24Z): the pod's restart identity is no longer in the settings hash, so a
    # restart that is not in this log stops dispatch ("unplanned"), a restart under way or aborted holds it, and a missing log is unknown (holds).
    # `host` is the entry's host in the log for the site_g settings command's pod.
    site_g_restart_log: str | None = "/mnt/volume2/icsa-2027/site_g_restart_log.jsonl"
    site_g_restart_host: str = "site_g"
    site_g_settings_every_s: float = 60.0
    # site_g's log volume /data (Traefik's and op_worker's logs; science, #2, 05:46Z): a command printing its free GiB; below the minimum
    # dispatch STOPS, an unreadable value holds it. Same forced-command key as the settings hash.
    site_g_disk_cmd: list[str] | None = None
    # The kept-log check (lane-faults: `python -m icsa.faults.calibrate logcheck --out DIR`): exit 0 fine, `log_check_stop_code` (4) = alarm, stops
    # dispatch; any other exit, a timeout or no run = unknown, holds it. None = not checked (required: holds). Off by default, unlike the checks around
    # it: science, #2, 2 Nov 08:15Z, it applies during fault calibration only and from the host with site_g's key, and the main runs leave no Traefik lines.
    log_check_cmd: list[str] | None = None
    log_check_stop_code: int = 4
    log_check_required: bool = False       # True: no command configured = unknown = dispatch held (set it when the check can run)
    log_check_every_s: float = 300.0       # its own, slower cadence: one ssh and two kubectl calls per run of it
    site_g_disk_min_gib: float = 15.0
    site_g_settings_timeout_s: float = 20.0
    # What the server reports it ran (icsa/servedsettings.py): another served model id, or a reported setting that differs from what was
    # requested, stops that model's dispatch until its name is listed in `served_release_file`. Extra accepted ids per model key (a backend
    # that names the model differently, found by the settings proof) go in `served_id_aliases`.
    served_check: bool = True
    served_release_file: str = "/mnt/volume2/icsa-2027/SERVED_SETTINGS_RELEASE"
    served_id_aliases: dict[str, list[str]] = dataclasses.field(default_factory=dict)
    # The short fixed read before each timed block (icsa/frprobe.py; science, #34, 2 Nov 10:07Z): a command (8 streams, 30 s, direct port, the warm
    # s2z file, a slot user's read token) printing {"mbit_s": ...}. Below reference x (1 - drop) the block does not start; unreadable holds.
    # The reference (this check on the study file, mean 4,925.1 Mbit/s since site_g's move: amendment 26(a)) and the drop are config. It runs only between blocks, never while a run is in flight.
    # On unless set off (a host without site_g, a test), and the event log says so: a launch cannot skip it by leaving it out. Its command, reference and
    # drop have one source (icsa/frprobe.py `configured`).
    read_check_required: bool = True
    read_check_retry_s: float = 300.0
    read_check_timeout_s: float = 180.0
    # Refuse to start on an unknown code version (a tree copied without .git and without a .code-stamp.json: icsa/codestamp.py).
    require_known_code: bool = True
    # A run that could not start its sandbox for want of a slot user (every user of its option in quarantine, or none in the map) used no attempt: an
    # attempt is a sandbox started (science, #2, 2 Nov 08:15Z). Users in ordinary use are a queue: the factory waits for them, with no time limit. The
    # count is per option, and `unstarted_stop_after` refusals of one option in a row stop ALL dispatch and alarm: one option refused while others run
    # would break the balance within a model that the analysis assumes (the lead, 2 Nov). A file written at `unstarted_release_file` after the stop
    # resets the counts and is removed: it ends that stop only (release.py).
    unstarted_stop_after: int = 5
    # A canary (science, #34, 3 Nov 01:08Z): while stopped, every `unstarted_canary_every_s` ONE run of the option at its limit may go (nothing else does, and none after the
    # hard stop); if it starts a sandbox the stop ends itself, if it is refused it uses none of that run's attempts. When the stop latches again within
    # `unstarted_relatch_window_s` of a canary ending it, `unstarted_canary_chain` times in a row, it stays latched for a person (the release file ends it then).
    unstarted_canary_every_s: float = 600.0
    unstarted_relatch_window_s: float = 3600.0
    unstarted_canary_chain: int = 3
    unstarted_release_file: str = "/mnt/volume2/icsa-2027/UNSTARTED_RELEASE"
    # A run lost to our own bug (an exception that is neither infrastructure nor an agent outcome: status `harness_error`) is not an outcome (science, #34,
    # 2 Nov 18:35Z). It uses no infra attempt, goes back to pending from the same row and seed when the campaign next opens (after the fix, a restart), and
    # `harness_error_stop_after` of ONE KIND (the exception's type name) in the whole campaign, all options and models together, total and not consecutive,
    # stop ALL dispatch (runs in flight finish) and alarm, so a bug cannot quietly drain one option. The count is kept in the store and a restart keeps it. A
    # file written at `harness_error_release_file` after the stop ends that stop only, is used once and is removed (release.py): restart with the fix first,
    # then write it.
    # Science, #34, 3 Nov 01:08Z (harness_stop.py): counted per kind and model from the store's attempts, in a window; the kind of a remote error is its inner type.
    harness_error_stop_after: int = 3             # of one kind on one model within the window: that model stops
    harness_error_window_s: float = 6 * 3600.0
    harness_error_models_stop: int = 3            # one kind on this many models in the window: ALL dispatch stops
    harness_error_option_stop: int = 5            # one kind this many times on one option across models in the window: ALL dispatch stops
    harness_error_release_file: str = "/mnt/volume2/icsa-2027/HARNESS_ERROR_RELEASE"
    # Spend before the campaign that counts against the Claude total (science, #34, 2 Nov 06:22Z: about $103 of test sweeps), a stated
    # figure in the spend alarm and the Sonnet gate's projection. 0 would hide it.
    past_spend_usd: float = 103.0
    past_spend_source: str = "science agent, #34, 2 Nov 06:22Z: about $103 of test spend (sweeps) before the campaign"
    # Sonnet gating (operator, 2 Nov 01:15Z; scheduling only, see gate.py): main-block Sonnet runs wait for `gate_calibration_runs` priced
    # calibration Sonnet runs and the first `gate_haiku_runs` Haiku main runs; a projected Claude total above `gate_max_usd` (or an
    # unknown one) holds Sonnet until `gate_release_file` is written, after that outcome: one older than it does not count. gate_model None = no gate.
    gate_model: str | None = "claude-sonnet-5-5"
    gate_haiku_model: str = "claude-haiku-5-5"
    gate_calibration_runs: int = 6
    gate_haiku_runs: int = 50
    gate_max_usd: float = 5000.0
    # What the gate's projection adds for the Claude coders (#76), in place of what they have spent and will spend (science, #34, 00:22Z, set at 00:28Z): dispatch
    # does not depend on coding's progress, so an unreadable or unfinished archive never holds Sonnet. A fixed figure. The coders' real spend still shows in the
    # spend alarm and the report (progress.coder_spend).
    gate_coder_allowance_usd: float = 1350.0
    gate_release_file: str = "/mnt/volume2/icsa-2027/SONNET_RELEASE"
    prices: dict[str, Price] = dataclasses.field(default_factory=default_prices)
    # The spend alarm (#34, science agent 1 Nov): fires when the spend so far, or the spend projected at the campaign's finish,
    # reaches this many USD, and whenever either cannot be computed. See progress.spend_alarm.
    spend_alarm_usd: float = 4000.0
    # More than this many ended attempts of one Claude model with no usage recorded raise an alarm ("something is losing usage records", science, #34, 22:58Z):
    # each is charged the bound in the spend whatever the count, and nothing is stopped.
    lost_usage_alarm_after: int = 5
    # The #76 inspection coders (Opus), outside the scheduler: their archive (`<work>/answers/<packet>/claude/attempt-*/meta.json`),
    # the packet directory (`queue.json`) and, until a queue exists, the expected number of packets. None = unknown (the alarm fires).
    coder_work_dir: str | None = None
    coder_packets_dir: str | None = None
    coder_expected_packets: int | None = None
    # A launch that does not say where the coders' archive is would show the spend as UNKNOWN in every status, all campaign (the alarm treats it as
    # over the limit): so it refuses to start (the lead, 2 Nov) unless `coder_spend_required` is set off, which the event log says. Needed: coder_work_dir
    # (the coders' runner's --work, with its answers/ directory, empty before any coder has run) and coder_packets_dir or coder_expected_packets.
    # This is about the spend alarm and the report only: the Sonnet gate does not read the coders (`gate_coder_allowance_usd`).
    coder_spend_required: bool = True
    # Cost per packet to use until one is measured (None = none: with packets to come and none finished the projection is unknown
    # and the alarm fires). Default $0.113 per packet: measured in #76's live coder smoke run (Opus only; the #34 capacity report
    # section 7 gives the same figure, $76 / 672 packets). A measured mean replaces it as soon as one packet is finished.
    coder_cost_per_packet_usd: float | None = 0.113
    # site_b: a second backend for every open-weight model (operator decision, 1 Nov). Per-model
    # concurrency caps (PLACEHOLDER: from the load test). A model absent here has no site_b backend.
    # No slots file: always up unless requests fail; paused after repeated 5xx/429.
    site_b_caps: dict[str, int] = dataclasses.field(default_factory=lambda: {
        "Qwen3.8-27B": 8, "GLM-5.3-Flash": 8, "DeepSeek-V4-Flash-0731": 2,
        "Gemma-4-31B": 4, "Qwen3-Coder-30B-A3B": 4})
    site_b_base_url: str = "https://host-26.invalid/api/v1"
    endpoint_fail_threshold: int = 3      # consecutive endpoint infra failures that pause a backend unit
    endpoint_pause_s: float = 300.0       # dispatch pause of the affected unit (HPC slot, site_b model, Claude model)
    # A model API refusing the key (HTTP 401 or 403, errors.KEY_REJECTED) holds that backend unit at its first occurrence and charges no attempt. While held, ONE
    # probe run of the unit is let through every `key_rejected_pause_s`; the hold ends when a probe run is accepted, so a renewed key needs no one awake.
    key_rejected_pause_s: float = 900.0
    endpoints_file: str = "~/icsa-paths/endpoints.json"
    # An endpoints.json entry whose `checked_utc` is older than this (or absent) is not up: not a dispatch candidate, counted 0 in
    # the derived site_a cap, and an alarm in the status. None = no freshness rule.
    endpoints_max_age_s: float | None = 120.0
    # site_a slot equality (#34, icsa.campaign.slot_equality): before a slot takes its first run its served model id, root and
    # max_model_len (GET /v1/models) and its fingerprint (endpoints.json, when the HPC agent writes one) are compared with the
    # model's other slots, and every slot with the model's registered pin (api id and checkpoint revision, from config/models.toml). A difference
    # takes the slot out of dispatch, and so does "unknown" (a field unreadable) while `slot_unknown_blocks` is set, as it is by default.
    # checkpoint_revision and fingerprint come from endpoints.json (the HPC agent), the fingerprint from a probe if absent.
    slot_equality_check: bool = True
    slot_unknown_blocks: bool = True           # the lead, 2 Nov: a slot not shown to serve its model takes no run
    # Amendment 41: "every deployment of a registered model that passes 24(f)'s identity gate takes runs ... No other ground admits or excludes one." 24(f)'s gate
    # on site_a is the served model id and the checkpoint revision against the model's pin (config/models.toml), which the slot gate always applies. False: only
    # that pin check admits or excludes a slot; the comparison with the model's other slots (root, max_model_len, fingerprint, ...) and a run's recorded
    # `system_fingerprint` differing from its slot's are recorded, logged as events and alarmed, and never block a slot nor retry a run. True (default): as before.
    # A launch for main sets false; a launch that sets it false is on the record (`safety_checks_off`).
    slot_peer_blocks: bool = True
    # Science's ruling, #34, 3 Nov 02:45Z: a model with no usable backend (all its endpoints down, unreadable or not shown to serve it; or its host unreachable) for this many
    # seconds counts as held at the seed boundary on its own, recorded with an event and a standing alarm; when it returns, its seed-1 runs go first. 0 turns it off.
    # Science, 3 Nov 03:27Z: so does a model whose host is held for this long by its disk or memory (the host's own cap is an ordinary wait, not a hold).
    no_backend_hold_s: float = 1800.0
    # Amendment 41(b), science #34, 4 Nov 01:49Z: a dispatch pass in which a model's next run was ready but every endpoint of the model was at its cap is a WAIT, counted per model; at most
    # one `endpoint_wait` event per model per this many seconds, and the cumulative count in the store (meta `endpoint_waits`) is flushed at the same cadence (scheduler._report_endpoint_waits).
    endpoint_wait_event_s: float = 60.0
    # Endpoint keys of models whose server sends no system_fingerprint by design (Coder: vLLM 0.15.0). A null fingerprint of such a
    # slot, with identity_checked_utc set, is "not provided", alarm-free; its checkpoint_revision is still compared.
    slot_no_fingerprint_models: list[str] = dataclasses.field(default_factory=lambda: ["qwencoder"])
    # Do not start a run on an HPC slot whose stack ends sooner than the run could last (site_b and Anthropic have no
    # end time). Derived, never a constant: pilot and calibration runs need `time cap + 2 min` (so none is cut by a
    # stack end; the pilot sets the caps). After the pilot the operator sets `slot_margin_s` from the pilot's measured
    # p95 wall time + 2 min; until then it is `time cap + 2 min` as well. `time_cap_s` overrides the harness config's cap.
    slot_margin_s: float | None = None
    time_cap_s: float | None = None
    slot_margin_slack_s: float = 120.0    # the 2 min: endpoints.json lags the real job state by up to 30 s
    poll_interval_s: float = 5.0
    # Host-memory watchdog (8 sandboxes x 16 GiB overcommits the 55 GB host, accepted by the science agent, 1 Nov): below the first value
    # of available memory no NEW run starts; at or above the second it resumes by itself. Nothing is ever killed. 0/None = off.
    # above earlyoom's SIGTERM (6% of the run VM, about 6.6 GiB) by one container's limit, 17 GiB, so that a run in flight can reach its limit
    # without earlyoom firing; the lead's decision, 2 Nov (not a registered limit). The order: pause > the scripted guard > earlyoom TERM > KILL
    host_mem_pause_below_gib: float | None = 24.0
    host_mem_resume_at_gib: float | None = 28.0
    retry_delay_s: float = 60.0           # before re-running an infra-failed run
    onedata_pause_s: float = 60.0         # the health gate's poll period: after a failed pre-run check no run starts on any host, and the dispatcher runs the check itself this often until it passes
    onedata_gate_check_timeout_s: float = 120.0   # one gate check that has not answered by then reads as down (never as a pass), and its late answer is ignored; no second check starts until it returns
    # Real sandbox image: a tag or id to resolve ONCE when the campaign first starts; its immutable id is stored in the
    # campaign state and every later start (a resume) must resolve to the same id unless `repin_image` (an explicit
    # operator decision) says otherwise. Empty: no real sandbox (stub runs). `pinned_image_id` is filled by the campaign.
    # From which runs the harness refuses sampling/reasoning settings that are not 'frozen': "pilot" (default; the sampling and
    # reasoning settings are registered before the pilot, science agent 1 Nov) or "main" (only past the pilot). The one place this is decided.
    enforce_frozen_settings_from: str = "pilot"
    sandbox_image: str = ""
    repin_image: bool = False
    pinned_image_id: str = ""
    # Two run hosts, split by whole models (icsa/campaign/hosts.py; science, #2, 2 Nov 05:36Z). Empty `hosts`: one host, as before.
    # hosts = {name: {remote, ssh, max_sandboxes, mem_pause_below_gib, mem_resume_at_gib, disk_min_free_gib, slot_keys}};
    # model_host = {model: host}, pinned with the slot keys in the campaign state at the first start (repin_hosts to change it).
    hosts: dict[str, dict] = dataclasses.field(default_factory=dict)
    model_host: dict[str, str] = dataclasses.field(default_factory=dict)
    repin_hosts: bool = False
    host_plan_file: str = ""            # the fixed map's source (tools/host_split.py's output): model_host must equal its map; pinned with its hashes
    host_probe_every_s: float = 15.0
    host_probe_stale_s: float = 60.0      # a remote host's last probe older than this: nothing new starts there (unknown is not ok)
    reap_at_open: bool = True             # real runs: what a dead dispatcher's leases left on this host goes at open(); what cannot go stays counted
    host_worker_deaths_pause: int = 3     # this many workers dying on a host within the window pauses it; one is that run's failure
    host_worker_deaths_window_s: float = 300.0
    host_pause_s: float = 300.0           # after a host failure, before a good probe may make it dispatchable again
    d_spool_gib: dict[str, float] = dataclasses.field(default_factory=lambda: {"S2": 3.79, "S1": 0.05})     # a D transfer's gate spool, by layout
    d_sandbox_gib: dict[str, float] = dataclasses.field(default_factory=lambda: {"S2": 4.54, "S1": 1.25})   # its sandbox: a D S2 run peaks at 8.33 GB
    # (S1: 0.75 GB base + 0.496 GB of an instance's daily files, from the layout index: results/multihost/s1_d_gb.json)
    # (science, #2, 20:20Z: the gate spools the whole file beside the sandbox for the last minute of the download, then deletes it; S1's figure is an assumption)
    local_disk_min_free_gib: float | None = None   # one host: the dispatcher's own disk floor (campaign root and docker root, the smaller); with two
                                                   # hosts the local host's `disk_min_free_gib` is used. Below it nothing new starts here, and the status alarms
    alarm_m_backlog_window_s: float = 1800.0   # M runs waiting for a slot user: an alarm when that count grew over this window and never fell below its start
    remote_lost_s: float = 600.0          # a run's host unreachable this long: the run is lost (infra), and stays counted until shown gone
    alarm_infra_rate: float = 0.10
    alarm_endpoint_down_s: float = 30 * 60.0
    # Runs pending, none in flight, none started for this long (since this process's first look): dispatch is held, whatever the
    # cause, and the status says so, so a loop with nothing dispatchable never waits silently. And the loop's own last look.
    alarm_no_start_s: float = 30 * 60.0
    alarm_dispatch_stale_s: float = 5 * 60.0
    # Infra-exhausted runs are never scored and never imputed; they are reported missing per cell, and when they concentrate in one option that is an
    # option-dependent loss (science, #34, 2 Nov 18:35Z: "tell me at once"). An option alarms when it has at least `alarm_exhausted_min` exhausted runs and its
    # exhausted rate (exhausted / its done-or-exhausted runs) is at least `alarm_exhausted_ratio` times the pooled rate of the other options, or the other options
    # have none. The 3 and the 2.0 are lane-int2's proposal, pending science's word (the time-cap diagnostic's ratio is 2.0 too). It stops nothing.
    alarm_exhausted_min: int = 3
    alarm_exhausted_ratio: float = 2.0
    # #34 load diagnostic (an alarm, not a rule; the time cap itself is unchanged): a cell whose share of runs stopped by the
    # time cap exceeds this, or whose site_b share is more than `alarm_timecap_ratio` x site_a's for the same model.
    alarm_timecap_share: float = 0.05
    alarm_timecap_ratio: float = 2.0
    alarm_timecap_small_n: int = 20       # below this many runs a 5% share is one run: the alarm text says so
    # Every deadline group (block 1, tiers A and B) runs to `hard_stop_utc`, the one setting of the deadline (its value is in the launch config, never in the code,
    # so moving it moves no hashed file), after which unfinished runs stay unfinished and are reported. Block 1's own earlier cut-off was dropped on 2 Nov
    # 03:52Z (operator, via science). UTC ISO. None = no alarms. `cutoff_utc` is only the fallback of an unset hard stop.
    cutoff_utc: str | None = None
    hard_stop_utc: str | None = None
    # Two settings, kept apart (science, #2, 2 Nov 11:54Z). Dispatch stops at the hard stop itself, alarms, and resumes only on the operator's word, a file written
    # after it at `hard_stop_release_file` and used once; nothing in flight is stopped. `cohort_cut_utc` only stamps: a run started at or after it is out of the
    # paper's cohort, kept, and reported descriptively. None: the snapshot's t minus the time cap (amendment 29(c)), see `snapshot_utc` below. A launch with no hard
    # stop refuses to start (the lead, 2 Nov), unless `hard_stop_required` is set off, which the event log says.
    cohort_cut_utc: str | None = None
    hard_stop_release_file: str = "/mnt/volume2/icsa-2027/HARD_STOP_RELEASE"
    hard_stop_required: bool = True
    # Amendment 29(c) and (g): two times the code never holds, so that no hashed file changes when they do. `snapshot_utc` is t of the fixed snapshot of the
    # paper's confirmatory analysis; the cohort is the runs first started by t minus the final time cap (`cohort_cut_utc` says another cut explicitly). It
    # cannot move after a main run has started. `quiet_window_utc` is the latest time of the quiet window of 29(g), which opens at it or when every
    # seed-1 run has started, whichever comes first; amendment 30(g) makes it the snapshot's cut, so a launch that requires its times refuses unless it is the cohort cut to the second: dispatch pauses for all options, runs in flight finish, and it resumes only on a file written at
    # `quiet_window_release_file` that names who and why, used once. A launch without either time refuses to start unless `launch_times_required` is set off,
    # which the event log says.
    snapshot_utc: str | None = None
    quiet_window_utc: str | None = None
    quiet_window_release_file: str = "/mnt/volume2/icsa-2027/QUIET_WINDOW_RELEASE"
    launch_times_required: bool = True
    # A passive signal between the read checks (science, #2, 2 Nov 11:57Z; the lead chose this alone for now): how much of the study file is in site_g's page cache, hourly, by a
    # command through the forced-command key. It prints {"warm_share": 0.97} or fincore's own "RES SIZE". The first reading is the reference; `fincore_drop` below it for
    # `fincore_sustained` readings in a row alarms. It stops nothing, and an unreadable one only says so. None: off, until the command is installed.
    fincore_cmd: list[str] | None = None
    fincore_every_s: float = 3600.0
    fincore_drop: float = 0.20
    fincore_sustained: int = 2
    # The live check (amendment 25(e); icsa/campaign/livecheck.py, probe: `python -m icsa.scripted live-probe`). Every `live_check_every_s`, while runs are in flight, a fixed scripted S1 read
    # of T and of M runs through its command in `live_check_cmds` ({"T": [argv..], "M": [argv..]}) on the dispatcher host, with its own slot user (`live_check_slot_keys`, passed as
    # ICSA_SLOT_KEYS). Two consecutive probes of one shape above `live_check_limit` x their single-run read time lower the total level by one step of `level_ladder` (the levels frozen
    # before the curve, ascending), for every cap together, and only the rise rule of amendment 29(f) (below) raises it again. A probe
    # that fails or cannot be compared is unknown: neither a pass nor a breach. No commands = the check is off; in a real launch (one with a sandbox image) that is named in
    # `safety_checks_off` unless `live_check_required` is set false, which is named too. `live_check_timeout_s` covers the probe's whole sandbox: a full S1 cell is minutes, not one.
    live_check_cmds: dict[str, list[str]] | None = None
    live_check_every_s: float = 1800.0
    live_check_limit: float = 1.25
    live_check_timeout_s: float = 5400.0
    live_check_required: bool = True
    live_check_slot_keys: dict[str, str] = dataclasses.field(default_factory=dict)       # {"T": "T-27", "M": "M-8"}: kept out of every host's slot_keys
    # How many files each shape's probe reads (amendment 25(e), "about a minute"): {"T": n_T or null, "M": n_M or null}, the FIRST n files of the cell's fixed order; null, or no entry, is the
    # whole cell. The launch JSON gives the numbers, never this file. The count reaches the probe as `--probe-files n` after its command's argv, and the probe compares only with baseline
    # records of that count (`baseline --probe-files`, a directory of its own); a probe whose line does not carry the count asked for is unknown.
    live_check_probe_files: dict[str, int | None] | None = None
    # Whether a probe holds a place in the level while it waits and while it is up (True: it counts in every cap, the level and its host's hold, as when the probe's sandbox is on a run
    # host). False: the probe's sandbox is on a third host that holds no user and no sandbox of either run host (science, #34, 3 Nov 02:47Z), so `_live_take_place` returns at once and
    # `_probe_places` stays 0; it still skips a round when nothing is in flight, since "under the real load" needs runs up.
    live_check_holds_place: bool = True
    level_ladder: list[int] = dataclasses.field(default_factory=list)
    # The level setting (science's rulings, #34, 3 Nov 00:28-00:31Z): the frozen levels go here, in the launch JSON (4, 8, 12, 16, 24, 32, 42), not in the code. `level_start_steps`: a real main
    # launch sets 1 (main starts one level below the curve's cap); at open() the level is at least that many steps down.
    # A restart adds its step through `python -m icsa.campaign level-down`, on top of what the store holds. The value in force lives in the campaign state, not in this file.
    # THE RISE (amendment 29(f), replacing the science agent's word of 25(e)): one step up at the first check, 2 h (`level_rise_after_s`) after the last change of level, with every live probe
    # within `live_check_limit`, no gate 5xx or reset in the attempts that ended in the window, and op_worker's resident memory up by under 5% over it. The memory is read from lane-mon's
    # provider_mon jsonl at `level_memory_file` (sample lines with a time at `level_memory_time_field` and the value at `level_memory_field`, dotted paths; a process id at
    # `level_memory_id_field` that changes inside the window means a restart). An input that is not known holds the level and the status alarms with which one.
    level_start_steps: int = 0
    level_rise_after_s: float = 7200.0
    level_rise_check_every_s: float = 300.0
    level_memory_file: str = ""
    level_memory_field: str = "opw.rss_mib"
    level_memory_time_field: str = "ts"
    level_memory_id_field: str = "opw.id"
    level_memory_gap_s: float = 600.0
    # site_g's memory, a campaign alarm that stops nothing (science, #34, 23:57Z): op_worker's working set over `SITE_G_MEM_OPW_MAX_PCT` of the node's memory, or the node's own use
    # over `SITE_G_MEM_NODE_MAX_PCT`, is an ALARM line, and op_worker's resident-memory growth per hour is reported over `site_g_memory_growth_window_h`. The reading is the newest `sample` line
    # of the provider monitor's JSONL (tools/provider_mon.py: node.mem_pct, opw.rss_mib, opw.ws_mib, opw.ws_pct_node, opw.id, ts), a COPY of site_g's /data/icsa-mon/mon.jsonl on this host: the
    # dispatcher holds no key to site_g, and the copy is made by something else. The path is a launch setting (the launch JSON); the percentages are the reading's own, never worked
    # out here from a constant, because site_g's memory has changed before. A missing, stale (older than `site_g_memory_max_age_s`, which must exceed the copy interval) or unparsable
    # reading is UNKNOWN, never a pass; `site_g_memory_unknown_alarm_after` unknown checks in a row alarm. On unless set off: with no path it reads unknown, and the event log
    # names it (`safety_checks_off`). The check runs every `site_g_memory_every_s`; a growth sample is kept every `site_g_memory_sample_every_s`.
    site_g_memory_file: str | None = None
    site_g_memory_required: bool = True
    site_g_memory_max_age_s: float = SITE_G_MEM_MAX_AGE_S
    site_g_memory_every_s: float = 60.0
    site_g_memory_sample_every_s: float = 300.0
    site_g_memory_unknown_alarm_after: int = 3
    site_g_memory_growth_window_h: float = SITE_G_MEM_GROWTH_WINDOW_H
    site_g_memory_growth_min_span_h: float = SITE_G_MEM_GROWTH_MIN_SPAN_H
    # groups whose projected finish is checked against the cut-off, in drop order (earlier = more protected)
    rate_window_h: float = 2.0            # window of the observed completion rate used for the projections (#34)
    min_rate_runs: int = 5                # completions in the window below which no projection is made
    deadline_groups: list[str] = dataclasses.field(default_factory=lambda: ["main_s1", "main_s2_a", "main_s2_b"])

    def provider(self, model: str) -> str:
        if model in self.provider_of:
            return self.provider_of[model]
        return "anthropic" if model in self.api_models else "site_a"

    def hard_stop(self) -> dt.datetime | None:
        return _zoned(self.hard_stop_utc) if self.hard_stop_utc else None       # not `cutoff_utc`: an old cut-off left in a config must not stop dispatch

    def cohort_cut(self) -> dt.datetime | None:
        if self.cohort_cut_utc:
            return _zoned(self.cohort_cut_utc)
        if self.snapshot_utc:
            return _zoned(self.snapshot_utc) - dt.timedelta(seconds=self.run_time_cap_s())      # amendment 29(c): runs first started by t minus the final time cap
        return None

    def run_time_cap_s(self) -> float:
        if self.time_cap_s is not None:
            return float(self.time_cap_s)
        from icsa.harness.config import load_config
        return float(load_config().limits.time_cap_s)

    def slot_margin(self, block: str) -> float:
        """Seconds a stack must still run for a run of `block` to start on its slot."""
        full = self.run_time_cap_s() + self.slot_margin_slack_s
        if block in self.barrier_blocks or self.slot_margin_s is None:    # pilot and calibration: always the full cap
            return full
        return float(self.slot_margin_s)

    def api_cap(self, model: str) -> int:
        """In-flight cap of one Claude model (its own entry; a model with no entry shares provider_caps["anthropic"])."""
        return int(self.anthropic_caps.get(model, self.cap("anthropic")))

    def site_a_cap(self, slots: list[dict] | None, models: set[str] | None = None) -> int | None:
        """THE site_a provider cap (scheduler, status and budget all call this): the sum of the per-slot session caps
        (`site_a_slot_caps`, measured, #34 capacity report) of the slots endpoints.json lists as up, for the open `models`
        given (None: every up slot). A model with no up slot adds 0; a slot whose key has no entry adds `default_cap`.
        None = slots unreadable or no per-slot caps configured: the caller falls back to `cap("site_a")`."""
        if slots is None or not self.site_a_slot_caps:
            return None
        keys = None if models is None else {self.open_models[m] for m in models if m in self.open_models}
        return sum(int(self.site_a_slot_caps.get(str(s.get("model")), self.default_cap)) for s in slots
                   if s.get("up") and s.get("slot") is not None and (keys is None or s.get("model") in keys))

    def cap(self, provider: str) -> int:
        return int(self.provider_caps.get(provider, self.default_cap))

    @classmethod
    def from_json(cls, path: str | Path | None) -> "CampaignConfig":
        cfg = cls()
        if path is None:
            return cfg
        raw: dict[str, Any] = json.loads(Path(path).read_text())
        for k, v in raw.items():
            if k == "blocks":
                cfg.blocks = [BlockSpec(**b) for b in v]
            elif k == "prices":
                cfg.prices = {m: Price(**p) for m, p in v.items()}
            elif hasattr(cfg, k):
                setattr(cfg, k, v)
            else:
                raise KeyError(f"unknown campaign config key: {k}")
        return cfg
