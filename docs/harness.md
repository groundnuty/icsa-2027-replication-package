# Agent harness (#8)

Derived from `handle_4/prior-study-replication-package` @ `06223f16181d53681b17e274aa2ccaec04ffbf06`
(`harness/panel.py` `ForgeOpenAILeg` loop, `runner.py`, `schema.py`). The commit is also in
`icsa/harness/config.py` (`BASE_COMMIT`) and in every run record (`extras.base_commit`).

## Layout
| file | role |
|---|---|
| `icsa/harness/loop.py` | the loop, `python` tool, caps, per-turn records |
| `icsa/harness/adapters.py` | OpenAI-compatible, Anthropic Messages, scripted stub |
| `icsa/harness/knowledge.py` | MCP stdio client for the knowledge plane (#6) |
| `icsa/harness/sandbox_api.py` | the #7 interface; `LocalSubprocessStandIn` is a test stand-in only |
| `icsa/harness/runner.py` | `execute_run` -> `run_record.json`, `transcript.json`, `code_cells.json`, `output/` |
| `icsa/harness/scheduler.py` | seeded shuffle, per-provider caps, resume |
| `icsa/harness/oracle.py`, `oracle_analysis.py` | scripted agent; its analysis is a literal implementation of the prompt's Method (not #4's code) |
| `icsa/harness/report.py` | validity of `report.json` / `mhw_mask.nc` per `report-spec.md` |
| `icsa/harness/errors.py` | `InfraError(kind, detail)` for the campaign (#16) |
| `icsa/harness/roundtrip.py` | one live tool-call round trip: `uv run python -m icsa.harness.roundtrip <model>` |
| `config/harness.toml`, `config/models.toml` | frozen parameters (placeholders) and the 7-model table |

## Differences from the base
* The Claude leg uses the Anthropic Messages API with the same harness-owned loop, not
  `claude-agent-sdk` (which lost the raw trace). Transcript and usage are recorded alike for all models.
* Bad tool-call arguments are reported back to the model as an error, not silently replaced by `{}`.

## Per-model tool-calling adaptation
* vLLM models: native OpenAI `tools`; `seed`, `temperature`, `top_p` as parameters; other sampling keys
  and chat-template kwargs through `extra_body`; reasoning text recorded in the transcript
  (`_reasoning`), and echoed back only where the model entry sets `echo_reasoning_field` (Qwen 3.8).
  Sticky slot per session (`slots.py`); retries on connection errors / 5xx / 429.
* Claude: `tools` with `input_schema`; **no** temperature/top_p/top_k/seed (vendor requirement; seed
  does not exist, `seed_honoured=false`); adaptive thinking and `output_config.effort` from config;
  thinking blocks returned verbatim with tool results.

## Sampling and reasoning sources
In `config/models.toml`, per model, with URL and section. GLM-5.3-Flash has no vendor sampling
recommendation (benchmark footnotes only), so none is set. Gemma FP8 alias guidance, DeepSeek
reasoning-passback and default effort are UNVERIFIED on the cards. Hugging Face cards were read
through a page summariser: re-check the numbers against the raw cards before freezing.
All entries are `collected-awaiting-freeze`; live study runs are refused until `frozen`.

## Contract with the campaign layer (#16)
`execute_run(run, attempt, run_dir, slot, config, concurrency_at_start=1) -> RunRecord`; `config` is a
`RunContext` (harness config, prompt texts, instances by id, factories). The campaign picks `slot`.
* `InfraError(kind, detail)` (`kind` = `endpoint` | `sandbox` | `knowledge`) is raised, after teardown, when
  the endpoint still fails (connection, timeout, 5xx, 429) after the transport retries, or the sandbox /
  knowledge server fails outside the agent's code (start failure, `exec` raising). `run_dir/infra.json`
  holds the diagnosis and the partial transcript; no `run_record.json` is written.
* Agent-code exceptions (non-zero exit), turn / token / time caps, a 4xx request error and report outcomes
  return as RunRecord terminations. Slowness is never infra.
* The scheduler (`scheduler.py`) is minimal: per-provider worker pools only. Ordering, resumption and retries are #16's.

## Protocol texts
The prompt is rendered from `protocol/task-prompt.md` and `protocol/access/*.md` (the registered protocol, a1b4c94) at
run time; there is no fallback copy. Slot values the protocol leaves to other lanes ({DATASET_ID},
{FS_EXPR}, {MOUNT_ROOT}, {SCRATCH}; and per layout {DATASET_LOCATION}, {MOUNT_LOCATION}, in `[prompt_slots.S1]` / `[prompt_slots.S2]`) are config
(`[prompt_slots]` in `config/harness.toml`), real values. Caps follow `parameters.md`
(provisional pilot values): 8,000 characters per tool result, 150 tool rounds, 4 M tokens, 240 min.

## Finished
`extras.finished` = the run ended with a final assistant message with no tool call before any cap or error
(`extras.ending == "final_message"`) AND `validate_outputs` accepts both files. `extras.ending` is one of
`final_message | turn_cap | token_budget | time_cap | error:<type>`; `extras.last_turn_no_tool_call` is
recorded as well.

## Measures in the run record
* `bytes_into_context`: UTF-8 bytes of the tool outputs as delivered after capping (exact).
* `tokens_into_context`: next call's prompt tokens minus the previous prompt and reply tokens
  (provider usage; an estimate; last turn counts 0).
* A run that exceeds the token budget ends as `token_budget` (new `Termination` value, added by #8,
  as `parameters.md` names it). "Tokens" = sum over all model calls of input + output tokens.
* Prompt caching (Claude only, #8): every Anthropic request carries `cache_control {"type":"ephemeral","ttl":"1h"}`
  at the top level (it follows the end of the conversation) and on the system block when there is one;
  placement is identical for every option and layout, and the markers exist only in the request body, never in
  the stored history. The API's `input_tokens` is only the uncached remainder, so `Turn.input_tokens`
  (and so `RunRecord.input_tokens`, P3's `log2_tokens` and the `{TOKEN_BUDGET}` check) is the sum
  `uncached + cache_creation + cache_read`; the three parts are recorded separately on each `Turn`
  (`uncached_input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`) and summed in `extras`.
  The campaign store keeps `cache_creation_tokens` and `cache_read_tokens` per attempt and prices them
  separately (`Price.cache_read_per_mtok`, `cache_write_1h_per_mtok`; default 0.1 x and 2 x the input price).

## M's fixed per-run set-up cost (#7, science ruling of 1 Nov)
Every fresh M or M+ mount pays about 5.6 s once, before the agent reads anything. It is part of what M costs: it **stays in M's
measured wall time and is never subtracted**. It is recorded per run, in the run record's `sandbox` metadata as `m_setup`, so readers can
see how much of M's time is set-up rather than reading. Absent for T, T-unpaginated and D (no mount).

| field | meaning |
|---|---|
| `m_setup.mount_wait_s` | `time.monotonic()` from the `docker run -d` of the oneclient sidecar to the FUSE mount appearing (the wait loop in `Sandbox._start_mount`). `None` for the stub mount, never 0. |
| `m_setup.storage_detection_s` | oneclient's own storage access type detection, from its log. It runs at the **first file access**, not at mount time, so the log has it only after a first read. `None` with `storage_detection_none_reason` when no start line is in the log, or the first start has no end line, or the log cannot be read; never 0. |
| `m_setup.storage_detection` | the detail: `start`, `end` (log time `mmdd hh:mm:ss.uuuuuu`), `result`, and `phases`, every detection the log shows. |

What oneclient 25.0 writes (`helpersCache.h`, real lines in `results/m-throughput/*.oneclient.log`): `Performing automatic storage access type detection
for storage <id> for file <guid> with forced proxy io mode: 0` (line 467), then `Storage '<id>' is not directly accessible to the client. Test file
verification attempts limit (5) exceeded.` (line 752). Its duration is the difference of the two stamps: 5.09-5.14 s in all 14 logs of results/m-throughput (6 bare, 8 sandbox), matching
the 5.59 s first file read. Straight after it the log shows a second detection, `forced proxy io mode: 1`, of 25-27 s. **The log does not say
whether the application waits for it**, so it is listed in `phases` and **not** added to `storage_detection_s`, which is the first phase only.
**Phase 2 does not block reads** (recorded data, no new run): in the 12 per-file runs of `results/m-throughput`, nothing stalls in the first 40 s after
phase 1. The largest gap between one file's end and the next file's start is at most 0.003 s; the slowest open+read of any file but each reader's first
is at most 0.57 s (a stall would be about 25 s); the first file's open+read is 5.16-5.28 s in every run, which is phase 1. The two S2 runs (one big file)
have no zero-byte second and read 27-52 MiB/s from second 0, and `agent-abm-s1` (per-step times, no per-file rows) is 5.59 s for the first step and at most
0.294 s for the other 59.
The only end line seen is "not directly accessible", so `result` is `not_directly_accessible`; a detection that ends otherwise has unseen wording,
records `None` with a reason, and needs the parser extended. `mount_wait_s` and `storage_detection_s` are separate costs and not additive claims:
the first is mount readiness, the second is paid at the first read.

## Waiting
* Merge of `protocol/` (PR #20), #7's access slots; the frozen parser (#13).
* Oracle on the real S1/S2 through each enforced path: needs #3 and #7 (`test_oracle_real_paths_waiting`).
* Knowledge-plane server command: #6.

## Backends and malformed tool calls (added 1 Nov)

* **Two backends for the five open-weight models** (operator decision): HPC slots from `endpoints.json`
  (`qwen-101`, ...) and one logical site-b slot per model, passed as `site-b:<model>` (config `[site-b]`:
  base URL, key file read at use time and never logged, per-model concurrency placeholders). The campaign
  (#16) chooses the backend; a session keeps one backend and slot for all its turns. Each record carries
  `backend`, `base_url`, the API model id, the real checkpoint and the `system_fingerprint`(s) seen
  (`extras.system_fingerprints`; they differ between backends). 429 and 5xx are retried with backoff;
  if they persist the run raises `InfraError(kind="endpoint")`.
* **A model with no up slot is paused**, not failed: `slots.paused_models` and `run_all(paused_models=...)`
  return such runs as `Completed(paused=True)` without running them.
* **Malformed tool-call arguments** (all models, all options, identical): arguments that are not a JSON
  object are never resent. The history carries `{"_raw": "<original text>"}`; the model gets an error
  tool result saying the call was not executed and must be resent as valid JSON (a normal tool round,
  agent side, never infra). `RunRecord.invalid_tool_args_rounds` counts the rounds with at least one such
  call; `extras.invalid_tool_args_events` logs round, call id, tool, error and raw text.
* **Oracle (re-derived from protocol a5e4400):** the pool of day of year d is every SST value within +-5
  calendar days of a baseline date with that day of year (windows reach 1991-12-27 and 2003-01-05); day 60
  has no pool and is the mean of days 59 and 61, taken before the circular 31-day smoothing; percentile
  `hazen`; sea cells are finite on the extended baseline and the target. Readings taken where the text is
  silent: `baseline_analysed` in its report is the extended range (the days the pools used); no value is
  pooled twice (windows of one day of year are disjoint).

## Final-review fixes (1 Nov)

* **Output truncation is not a finished run.** A reply without tool calls whose stop reason is `length`
  (OpenAI) or `max_tokens` (Anthropic) ends the run as the new `Termination.OUTPUT_CAP` (ending
  `output_cap`, never finished), for every model; the stop reasons are in `extras.stop_reasons`.
* **Slowness is never infra.** A read timeout (request sent, response slow) is waited out within the
  run's wall time and ends as `time_cap` (`read_timeouts` counted in the adapter info). Only connection
  failures (including connect timeouts) and persistent 5xx/429 raise `InfraError`.
* **Tool-context size is measured, not inferred.** Per tool result and per turn: exact characters and
  UTF-8 bytes (`Turn.tool_output_chars/bytes`, `chars_into_context`, `bytes_into_context`). A token
  count exists only where a provider tokenizer is used (vLLM `/tokenize`, after the run), labelled in
  `extras.tokens_into_context_source`; otherwise `tokens_into_context` is null, the source says
  `unavailable` and `extras.tokens_into_context_reason` says why. It is descriptive and never averaged as
  a zero: site-b has no `/tokenize` and Anthropic's counting endpoint is not used, so a mean of it covers
  site-a's runs, and `tokens_into_context_runs` stands beside it. The earlier usage-difference figure is removed.
* **`execute_run(..., provider_cap=None)`** records the effective provider concurrency cap in
  `RunRecord.provider_cap` next to `concurrency_at_start`.

* **A read timeout abandons the request** (`RequestAbandoned`): never resent, the run ends as `time_cap`,
  and the adapter info records `abandoned_request: {reason: read_timeout, usage: unknown}`. The Anthropic
  SDK's own retries are off (`max_retries=0`); the adapter retries only connection failures and 5xx/429.
* **`RunRecord.model_version` follows the backend**: per-backend notes in `models.toml` (`version_notes`:
  `hpc`, `site-b`) plus the observed `system_fingerprint`s. `provider_cap` defaults from the config.
* `slots.paused_models` now takes `(pool, cfg, models)`.
* **Abandoned requests are persisted**: `extras.abandoned_request` (`read_timeout` or `deadline`, usage
  `unknown`), `extras.read_timeouts`, and `RunRecord.usage_complete` (False whenever a request was
  abandoned, so token totals are known to be incomplete). Malformed tool-call arguments are counted
  before any cap check, so a capping round's malformed call is still logged (never executed).

## Rulings of 1 Nov (PR A)

* **Oracle sea cells** (protocol 42bec0c): finite on every day of the target period only; baseline NaNs are
  ignored by the pools. `baseline_analysed` stays the single envelope of the days used (the extended span).
* **Knowledge-plane infra** is server-side only: connection closed or a crashed server, JSON-RPC internal
  error, unreachable. A tool error the server returns for the agent's own bad arguments (including invalid
  params and an unknown tool) is a normal tool round.

## What ends a cell, and what the agent is told (#34, science's rulings of 2 Nov)

**One cause per run,** whichever was noticed first (`killcause.PRECEDENCE`): `earlyoom`, `container_dead`, `host_oom`, `memory_limit`, `time_limit`, `killed_other`, `unknown`. It is in the run record's `extras.cell_kills.cause` and in `infra.json`. A retry keeps the 3 attempts of `parameters.md`.

| cause | what happens to the run |
|---|---|
| `earlyoom`, `container_dead`, `host_oom`: the host's doing | ended and retried, kind `sandbox` |
| `killed_other`, `unknown`, or memory counters that could not be read: the harness lost track | ended and retried, kind `unattributed_kill`, counted per option and model in `export_infra`'s `retries_by_kind`, since this can discard an agent's own outcome |
| `memory_limit`, `time_limit`: the agent's own | kept as its outcome |
| an exception in the agent's code, or output that is not UTF-8 | kept as its outcome |

**The agent's time ends for every process at once.** At the cap, and at the end of the agent loop, every process of its container is killed except its init and the init's `sleep`, and `collect` does it again first, for every caller; the container stays up because its cgroup's counters classify the kills. A process still in D or Z after SIGKILL runs no more of its code, so it counts as stopped. If the processes cannot be listed, or one is still running, the collection fails.

**A cell's clock starts when `exec` is entered,** and the run's cap when the agent loop starts, after the sandbox is up: M's mount set-up neither eats nor extends the cap. It stays in the measured wall time (`m_setup`). `cells.jsonl` has each cell's `pre_exec_s`.

**earlyoom's target is the sandbox's own process (science, #34, 2 Nov).** The hosts run `EARLYOOM_ARGS="-m 6,3 -r 3600 --ignore ^(dockerd|containerd.*|sshd.*|systemd.*|tailscaled|icsa-driver|dbus-daemon|.sd-pam.|docker|ssh)$"` (`earlyoom.EARLYOOM_ARGS`; the preflight and the campaign read the running service's own arguments, and refuse a host without those names). earlyoom can only exclude, and goes by `oom_score`, so every process of the agent's container, and of the control's, has `oom_score_adj` 1000, which outranks everything else while one exists; the kernel's OOM killer picks the same way. The gate and oneclient stay at 0, below every agent process: picked only with no agent process left, and what they lose is earlyoom's by role, retried, not a data fault. A `docker exec` client that dies anyway is seen, since the cell's own `timeout` is still running, whatever the exit code: what it left is killed and the run retried.

**A failed copy never loses its source.** When `collect` fails, `stop` moves the sandbox's disks to `<work_root>/_kept_evidence/<sid>` instead of deleting them, and `infra.json` has the path. Nothing removes them: check that directory after a campaign.

**The agent is told one fixed line, the same words in every option** (`loop.py`, `kill_note` and `ToolBox`):

- `note: the cell was stopped because it reached the memory limit of 16 GiB. The run continues.`
- `note: a process of this cell was stopped because it reached the memory limit of 16 GiB. The run continues.` (a worker; the cell ended on its own, science's wording of 2 Nov)
- `note: the cell was stopped because the run's time cap (240 min) was reached.`
- `note: the cell was not started because the run's time cap (240 min) was reached.`
- `note: the cell was killed (exit code N); the cause is not known. The run continues.` (only when a sandbox gives no record of the kill: one that does, and attributes nothing, ends the run)

## Sandbox and run limits (#8/#9, science rulings of 1 Nov)

Identical in every option and layout; none is tuned per option, layout or model.

| limit | value | where |
|---|---|---|
| time per cell | none of its own: the run's remaining time cap (`time_cap_s`) | `loop.py` hands `deadline - now` to `exec` |
| memory (agent's allowance) | 16 GiB; the container limit is 16 GiB + the tracer's **measured** headroom of 1 GiB = 17 GiB. The headroom was measured at +0.24 GiB on the naive whole-grid pattern (7.80 GiB untraced, 8.04 traced), and 1 GiB was confirmed by science on #9; it has no default (the real factory refuses to start without `tracer_headroom_gib`) | `[sandbox_limits]` |
| CPU | 4.0 (a cap, not a reservation) | `[sandbox_limits]` |
| pids | 512 | `[sandbox_limits]` |
| open files | 1,048,576, soft = hard (`--ulimit nofile`) | `[sandbox_limits]` |
| tool output | 8,000 characters per result | `[limits]` |
| `max_output_tokens` | 32,768, or the model's own maximum if lower (`ModelSpec.max_output_tokens`) | `[limits]` |
| host memory | dispatch pauses below 24 GiB `MemAvailable`, resumes at 28 GiB (the lead, 2 Nov: above earlyoom's TERM by one container's limit); kills nothing | `CampaignConfig.host_mem_pause_below_gib` / `host_mem_resume_at_gib` |
| sandboxes in flight | `max_sandboxes_by_block[group]`, else `max_sandboxes`; pilot and calibration at `main_s1`'s, tier B's S2 at `main_s2_a`'s; rule below | `scheduler._next_dispatch` |

A cell stopped by a limit ends with one fixed line naming the limit (16 GiB, or the run's time cap in minutes); only the exec'd process dies and
the run goes on. Kills are counted per run (`extras.cell_kills`). Cause: the agent's own allocation hitting the container limit (`memory.events`
`oom` moved) is the agent's outcome and never retried; a host OOM, an ancestor cgroup's limit or a dead container is infrastructure and retried;
a 137 of unknown cause is `unknown`, the run continues, no retry. Per container (agent, gate, sidecar) CPU seconds and peak memory are read before
teardown (`extras.containers`); ENOSPC is counted per run (`extras.enospc`, a lower bound: an error the agent's code caught is not seen).

`os.cpu_count()` reports the host's 16 CPUs inside a 4-CPU container, in every option. This is left as it is and stated here.

### The per-block cap (science, #9, 18:47Z)

Every run in flight stays within its own block's measured cap, counting everything in flight. A block-1 run (main S1 + pagination; pilot and
calibration use block 1's cap) starts if the total in flight after it is at most cap 1, and at most cap 2 while any S2 run is in flight. An S2 run
(tier A or B) starts only when no block-1 run is waiting for a sandbox (eligible, its own model's endpoint free, only the sandbox missing) and the
total after it is at most cap 2: S2 uses only spare capacity. A block-1 run held back by its own model's endpoint does not count as waiting. Each
wait of a ready block-1 run for an S2 run to finish is logged (event `block1_waited_for_s2`, meta `block1_waits`, shown in the status).

The assumption: a mix of the two blocks at a total of at most cap 2 is no heavier than cap 2 of S2 alone (an S1 run reads about 0.43 GB against
S2's 3.79 GB). The live time-cap alarm watches for it.

### Order before and around the main block (amendment 29(g))

The pilot and calibration's agent runs run together under block 1's cap, and both still hold main back until none of their runs is pending
(`CampaignConfig.concurrent_barrier_blocks`; `[]` restores the old order, pilot then calibration). Before the go (`past_pilot` false) both are
dispatchable; the go gates main only. The two share one read check (it runs between blocks, with nothing in flight). Within one model the pilot
keeps its priority over calibration under `priority_mode = "per_model"` (the pilot model's calibration runs start once its pilot runs have all been
dispatched); `"strict"` serialises them again. Fault calibration and the direct-path validation set run in their own processes, each holding a `flock` on a file of its own under `reservation_dir` while it runs
(`icsa/harness/reservation.py`; the kernel frees it when the process dies). The launch JSON says what each holds (`process_reservations`: `sandboxes` and `slot_keys`);
while a lock is held its sandboxes count in every cap and in the local host's own, and its slot keys are out of the campaign's local pool, so no agent run starts on
a user that fault calibration's attribution windows read. A lock that cannot be read counts as held and the status alarms. Both processes take `--launch-config` on
`run` and lease only from their keys; without it a real `run` refuses. Fault calibration runs the replacements of lost runs first, then the old site-g's finished runs again (science, 3 Nov: all of them, whatever they
showed, so the primary table is one VM and one head), then every planned run not yet done, in the sealed plan's order; the plan and its hash are not
touched. `run` puts a done run whose record carries no tags of its own back in the ledger as `rerun` (`Ledger.rerun`; its attempt count back to none), and
the rerun takes the next free run key (`-a2`), so the old run's directory and record are never written; `score` reads the reruns for `h3_table`, and
writes the old runs from their kept records as `h3_table_old_site-g_apart.csv`. The calibration's and the pilot's S2 runs start under block 1's cap, and
while one is in flight the S2 cap of its model's tier holds on everything, as for a main S2 run. `python -m icsa.faults.calibrate score` writes `h3_table_without_old_site-g.csv` beside `h3_table.csv` when some runs have tags
written after them (a `RUN_TAGS.json` entry), and names the runs with no tag at all.
