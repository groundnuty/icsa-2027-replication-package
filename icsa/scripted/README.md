# Scripted reference pipeline (#12)

Runs a scripted analysis through every data path, with no model in the loop. It answers four questions: does each enforced path deliver the right data, what does a run cost, how much concurrency does the federation take, and when does pre-provisioning (M+) pay off?

## What one run does

- **A fresh sandbox per run**, from `icsa.sandbox`, with an image built from the same snapshot as the code.
- **One script for every option** (`insandbox.py`). Only `Paths.open_path` differs:
  - T and T-unpaginated: a remote fsspec file;
  - D: `fs.get`, then the local copy;
  - M and M+: the mount.
- **Files chosen by name**, from the instance's required days. A separate listing step only records its entry count. Under T and D the listing returns the first 1,000 entries, which hold no required day, so using it would measure the known truncation and not the path.
- **#4 in computed mode inside the sandbox**, on the arrays it just read: `computed_fields`, `sea_cells`, `detect`. It does not use `refdet.ground_truth` or the field cache, which read local files on the host.
- **The required extent only:** 1,452 baseline days plus 92 target days, 60 x 60 cells. It is never widened to the 4,028-day pooling superset.

## What a result is compared with

Only what #5 froze: `cell_masks.npz` (checked against its sha256 in `instances.json`), and each record's `events` and `active_mask`. Equality is exact.

- A run's SST hash must also match a hash built from the local copy #3 verified. If no reference is available, the check reports unknown and the run does not count as equal.
- The coordinate check only identifies the cell: tolerance 1e-5 deg, because the dataset's float32 coordinates lie up to 3.97e-6 deg from the grid.

## Per-run record (`runs/<key>/run.json`)

| Measure | Source |
|---|---|
| Wall time | `Sandbox.exec`; plus stamps inside the script: client ready, listing done, first compute, read done, compute done |
| Bytes moved | Counters per container: agent `eth0` (the method in `parameters.md`), the gate's upstream interface (matched by MAC), and for M the oneclient sidecar on the bridge. `between_sites_rx` is the gate's upstream, or the sidecar's |
| Provider I/O and client requests | The gate log per request (T, T-unpaginated, D). For M, a separate `perf` pass with `--log-read-write-perf`, never timed, because that flag's overhead is unmeasured |
| CPU and memory | Per container (agent, gate, sidecar), from its cgroup: CPU seconds over the run, peak memory and OOM kills (science, #9). Inside the script: wall time and CPU seconds of the read and of the compute, to show which limit a level hit |
| Contention | Load, `MemAvailable`, free disk, other lanes' sandboxes, host `ens3` rx before and after |

A failed run is recorded and never retried, because an error is a result the cap rule needs. `--resume` adds a next attempt and keeps the earlier one on the record.

## What is not controlled

- **Provider page cache.** It can't be cleared without touching production, and all the pilot instances share the 1,452 baseline days. The pilot order is therefore a seeded permutation, and results are labelled "client caches fresh; provider cache not controlled".
- **Host page cache.** It is not dropped, because that would evict other lanes' caches. Fresh mounts and disks already give each run an empty client cache (`sandbox/INTERFACE.md`).
- **Host load.** It is recorded per run, not controlled.

## Running

Runs come from a git-archive snapshot, with `ICSA_RUN_SHA` and `ICSA_SANDBOX_IMAGE` set; the driver refuses otherwise. Run unsandboxed, because it uses docker and the federation. A batch's audit-log state is `ICSA_AUDIT_LOG` (default `off`), recorded in its manifest.

The calendar is science's, on #12 (1 Nov 17:30Z, revised 17:49Z, which wins). On site-g: perf-log overhead, the tracer's compact fix, **step A**, curve block 1, curve block 2, then the chosen level again with the audit log on, then the pilot and calibration.

```
# step A: 24 traced, enforced runs (T, T-unpaginated, D, M x S1, S2 on I35, I37, I48), serial, each required exact; plus one untraced pick per cell
# for the tracer's ratio. Stops after 2 failed runs. The overhead controls are not in it (--controls adds them)
python -m icsa.scripted baseline --out DIR [--instances I35,I37,I48] [--k 3] [--untraced-k 1] [--max-failures 2]

# the curve, per block, as that block's mix of cells, searching UPWARD (science, #2, 2 Nov): 2,4,8,12,16, stopping at the first
# failing level; the cap is the last passing level, never above --max-level (the site-g capacity benchmark's safe level; hard maximum 16).
# The cap goes to DIR/curve_cap_block<N>.json. If level 2 fails there is no cap and the command exits non-zero. A restart skips the
# levels already in curve_decisions.jsonl. --dry-run prints the plan. Block 2's result goes to the science agent before it is applied.
python -m icsa.scripted curve --out DIR --block 1 --baseline A_DIR --max-level 8 [--dry-run]
python -m icsa.scripted curve --out DIR --block 2 --baseline A_DIR --max-level 8
# the chosen level again with the audit log on: ICSA_AUDIT_LOG=on, --levels L --stop none --rep 2

# what the other lanes read: the dossier's scripted_pipeline and scripted_timing (blocks["1"|"2"]["cap"] and ["wall_at_cap_s"]),
# the analysis's overhead file, traced vs untraced
python -m icsa.scripted report --out DIR --single A_DIR --curve B1_DIR B2_DIR --overhead A_DIR --tracer-compare A_DIR

# the work that moved into the campaign, as config only (nothing runs): the overhead controls and k = 5 pairs, and the M+ window
python -m icsa.scripted plan-campaign --out FILE.json

python -m icsa.scripted smoke --out DIR --instance I35 [--only D:S2]      # correctness, untraced
python -m icsa.scripted perf  --out DIR                                   # M's request counts, never timed
python -m icsa.scripted.summarize DIR
```

**Tokens (`tokens.py`).** Every run holds a lease from the configured `TokenSource` for its whole life and mints its REST token, or its oneclient token (and M's sidecar's), through it; the record gets `token` = {source, subject, slot, start_utc, end_utc}, the interval to join to the audit log. The default is admin. The 24 baselines run on slot-user tokens only: `baseline` refuses to start unless `ICSA_TOKEN_SOURCE=pkg.mod:factory` names a source whose `kind` is `slot` (from the slots lane, `feat/8-slot-tokens`). `ICSA_TOKEN_SOURCE=icsa.scripted.slot_tokens:factory` is that source: it takes lane-slots' `icsa.harness.real_sandbox.leased_token` (branch `feat/8-slot-tokens`), waits for a free slot user of the run's option, mints the one token as that user (REST for T, T-unpaginated, D; oneclient for M) and releases on every exit; the run record gets `onedata_slot` {slot, user_id, start, end, wait_s, token_record}. No fallback to admin: M+ has no slot and fails; M+ and the WAN anchor run on the admin source. A run that cannot get a lease is recorded as failed, not retried. The oracle's post set goes through lane-slots' lease in its own driver (once `feat/8-slot-tokens` lands); it is not on this seam.

**The background queue** (in `plan-campaign`'s config, `queue`): from go, one sandbox at a time, inside the global cap, lowest priority, detached and resumable; the overhead pairs and M+ with M cold on site-f, then the rest of WAN, then the oracle's `--set post --cells T:S1`. Nothing in it runs during the baselines, curve, pilot or calibration. WAN's `--pause-file F` stops the batch before its next run while F exists. The batch already running comes from an older snapshot: `tools/scripted/pause_wan.sh RESULTS_DIR` waits for its next finished run, TERMs its python and checks no `icsa-sbx-s12-wan-*` is left; `tools/scripted/resume_wan.sh RESULTS_DIR` restarts it detached from its own snapshot without repeating finished runs.

**The memory guard of a level** comes from step A: the largest baseline run's agent + gate + sidecar peaks, summed, x 1.15 (`--mem-per-run-gib` overrides). A level whose runs do not fit in `MemAvailable` with 8 GiB kept free is dropped, never pushed, and the manifest says so: if 16 does not fit the top level is 12, because a host OOM would invalidate the measurement. Each run records `oom_kills` per container.

**The audit log (since 1 Nov 20:55Z it is ON at site-g).** Run the baselines and the curve with `ICSA_AUDIT_LOG=on`: `baseline` and `curve` REFUSE to start unless it is `on` (non-zero exit, a clear message; science, #85, 21:38Z); the manifest records the state. The other subcommands print a warning. (Whether the separate "repeat with the log on" step drops is the science agent's to confirm.)

**The audit log, as recorded.** `ICSA_AUDIT_LOG` (default `off`) is recorded in every manifest. The baselines and the curve run with it as it is when they start, labelled; the report's `audit_log` reads `mixed` when the batches differ. It blocks go regardless (criterion iv).

**What the dossier reads.** `scripted_timing.json` has, per block, `cap` (each run against the median single run of its own instance: the amendment's rule), `cap_dossier_rule` (the dossier's, with the worst single run as the baseline), `cap_rules_agree` and `wall_at_cap_s`. A `--baseline` directory holding curve or pooled runs is refused.

**Levels above 16 are refused,** because they need an explicit decision.

**Traced by default.** Step A and the curve carry #9's tracer, through the harness's builder (`icsa.harness.real_sandbox.ensure_instruments`). A traced run refuses to start without it, and must prove it ran: an import failure of the tracer, or an empty trace, is an error. `--untraced` exists only for the comparison.

**What a cap may rest on** (`curve.clean`): a run that finished clean, with the OOM counter of every container its option has known to be zero. An unknown counter does not pass. A mix's padding runs enter no statistic.

## The duty-cycle curve (`duty.py`; science, #34 05:21Z and 05:27Z, #2 item 6)

Science's order: registered curve, then the pilot at that cap, then the data share per option, then this curve, then an amendment for main if justified. Same pass rule as the registered curve (`curve.level_table`, both ratios, each at most 1.25x its own instance's single run); the load is agent-shaped: each slot repeats the block's mix with an idle gap after every run, so the cell's read phase is its pilot share of a cycle. Every counted run is a probe.

```
# 1. offline, no sandbox: freeze the schedule from the pilot's run records and the registered curve's baselines (levels frozen with it)
python -m icsa.scripted duty-profile --out DC_DIR --block 1 --baseline A_DIR --pilot CAMPAIGN_DIR --levels 8,12,16,24,32 \
    --share-from T-unpaginated/S1=T/S1,D/S1,M/S1
# 2. on site-g, as the registered curve (same env, ICSA_AUDIT_LOG=on), with the profile; a new --out; levels above 16 need --above-16-decision URL
python -m icsa.scripted curve --out DC_DIR/curve_b1 --block 1 --baseline A_DIR --duty-profile DC_DIR/duty_profile_block1.json \
    --levels 8,12,16,24,32 --max-level 32 --above-16-decision URL
# 3. the table: curve_decisions.jsonl carries each level's rows (both ratios, pass or fail); report gives scripted_timing.json as for the registered curve
#    (report fails a duty level as the curve did: a recorded failure, a pacer wait over 1 s on a run, a level with part of its plan or no decision line;
#    scripted_timing.json lists them as the block's duty_failed_levels)
python -m icsa.scripted report --out DC_DIR/report --single A_DIR --curve DC_DIR/curve_b1
```

**Shares before the pilot (amendment 28, correcting 25(c)).** `s(o, l) = min(1, 1.5 x R(o, l) / W(o, l))`, `W(o, l) = W(l) + R(o, l) - R(T, l)`: R is each cell's median baseline read phase (all instances pooled), W(l) the 10th percentile of the sizing runs' T walls on the layout, censored runs at their `wall_time_s` (their time so far at the cut-off). Offline, no sandbox:

```
python -m icsa.scripted.duty shares --block 1 --baseline A_DIR [A_DIR ..] --sizing results/34-sizing/manifest.jsonl --out results/34-shares/shares_block1.json
python -m icsa.scripted duty-profile --out DC_DIR --block 1 --baseline A_DIR --given-shares results/34-shares/shares_block1.json \
    --levels 4,8,12,16,24,32,42 --climb 8,16,24,32,42 --floor-level 2
```

The shares file is exactly `--given-shares`' input (one entry per cell of the block, `share` and `source`; a `provenance` object beside them is for readers). `--given-shares` takes shares as given and recomputes none; the whole provenance is in `source` (R, R(T), W(l) and its method, W(o, l), the factor, whether the cap at 1 applied, the sizing manifest's and each baseline directory's sha256), so it enters the profile's hash. A cell with no clean baseline read, a layout with no sizing run, a non-positive W(o, l), a stopped run the manifest's `cutoff_done` does not list, or an existing `--out` fails; T-unpaginated takes the formula like the others (the baselines run it in both layouts). `--w-method linear|nearest-rank` (default numpy's linear interpolation, as the pilot shares' p90; the amendment does not say which): block 2's W(S2) is 834.68 s by the first and 634.4 s by the second on the real manifest. **The shares file and the profile are never written inside what `icsa/codestamp.py` hashes** (icsa/, config/, protocol/, tools/, pyproject.toml, uv.lock): both commands refuse such an `--out`. They live under `results/`; a change of either is a new file and so a new `profile_id`, which every decision line carries.

**The ladder (science, #34, 3 Nov 00:33Z).** The profile freezes `--levels 4,8,12,16,24,32,42`, the `--climb 8,16,24,32,42` subset that runs in order, and `--floor-level 2` (the one level below the first, hashed with the rest; nothing about the ladder is a constant in `icsa/`). `curve.sequence_state` is the one pure function of the frozen levels and the results so far, and `curve.run_sequence` drives it for `curve` and `curve-multi`: the climb goes up while levels pass; a failing climb level tests the frozen level directly below it, then the next one down, until one passes or the climb's last pass is reached (16 fails: 12 runs; 12 fails: 8 is the cap; 24 fails after 16: 16; 8 fails: 4, then 2). A level the sequence did not ask for never runs, and a line for one makes `cap_from_decisions` raise. A rerun under 25(d) is a profile whose climb is the first curve's cap alone (`duty-profile --rerun-against PROFILE --first-curve DIR`), so it steps down from there and never above. A profile without a climb or floor runs every level in order to the first failure, as before; the registered flat-out curve (`curve` without `--duty-profile`) is not touched.

**Decision lines (duty-cycle).** Beside the verdict each line carries `ladder` (the profile's sequence), `ran_on` (`two_hosts`, the sandboxes per host, and per host the M slot users seen on its M runs and its configured share where known) and `m_reads` (one entry per counted M run, its own sandbox and mount: host, slot, M user, read phase, the single-run read phase of its instance, their ratio, the number of per-day reads and their median; a figure the record cannot show is null with `not_shown`, never 0). A failing line has `failed_on` and `m_bound` (true when the level fell on M's bound alone). `python -m icsa.scripted.duty main-cap` reads the lines into the cap, says `final` (exit 2 when a curve has more due, the cap then provisional; exit 3 with `NO MAIN CAP` on stderr when a finished curve has no cap, amendment 30(i)), says `start_equals_cap` (true when no level below the cap was run: main then starts at the cap), which level capped each curve and whether M bound it (`m_bound`, `cap_bound_by`); `--first-profile` / `--rerun-profile` name the profiles whose ladder the lines must agree with.

**A run's share** (eligible: the pilot's runs, `block == "pilot"` and not excluded from analysis, and the calibration's, `block == "calibration"`, whose load is real though every outcome analysis drops them; not an infrastructure failure; time-cap stops count; a stub model's record fails. The pilot is S1 only, so S2's shares come from calibration; T-unpaginated is in neither, so its cell fails unless `--share-from T-unpaginated/S1=T/S1` (or another source) is given, which the profile records; the block is part of a run's identity, so a pilot and a calibration run of one instance, model, seed and option are both kept). The run's window is the one its `wall_time_s` measured: `started_at` plus the slot-user wait (`extras.onedata_slot_wait_s`) for `wall_time_s`, not built back from `ended_at`, which is taken after validation; a record without the wait gets `[started_at, ended_at]` (named in the row's `window`), and one without `started_at` fails. T, T-unpaginated, D: the gate stamps a request at its completion only, so the time share is estimated, each forwarded request busy for min(time since the previous completion, 1 s); the byte share is measured, bytes site-g served (per gate tag the larger of `bytes` and `upstream_bytes`, the same counter as the scripted baselines) per second of wall over the scripted cell's rate while reading. The run's share is the larger. M: oneclient's perf log, FsLogic reads and ReadCache prefetches each busy for their own duration, gaps of at most 1 s between them bridged as the gate rule counts them; listing and metadata are not in that log, so M's share is low by their time. A cell's share is the **90th percentile** of its runs' shares (science, #34, 15:10Z; numpy's linear interpolation); mean, median and per-model means are beside it in the profile.

**The schedule.** Gap after a run of (option, layout, instance) = its single-run read phase / share - its single-run `total_s` (the whole run, sandbox start to teardown: a slot is busy for all of it before its gap starts, as the pilot's `wall_time_s` includes the agent's sandbox start); negative is 0, flagged `loaded_above_share`. **The cycle is held fixed** (the lead, 2 Nov): a run that took longer than its baseline idles less by the overrun, never below 0, so a slowdown on the host does not lower site-g's load; runs left with no gap are listed in the decision line's `cycle_overruns`. Each slot starts at a seeded offset within one cycle and runs one uncounted warm-up cycle; gaps carry seeded jitter of +-50%; padding keeps the run-and-gap pattern. No barrier lines the slots up. The profile is hashed; every decision line carries `duty_profile_id`, and its `baseline_id` is composed with it, so a resume under another profile is refused.

**Guards.** At most `--max-m-runs` (16) M runs at once (science's ruling: M x 16 was shown on site-g, 2 Nov) and at most as many sandboxes as memory holds (`max_live`, from the baselines' peaks); a counted run that waited records `pace_wait_s`, and the decision line lists runs that waited over 1 s (`paced_waits`). **A level with any such run fails** (`failed_for`): its offered load was capped, so a pass would not show the level holds it. Padding never waits for a slot. **A level also fails unless every planned counted run is recorded once and each cell has at least 3 reads** (`duty.level_gaps`; `coverage_gaps` in the decision line). Levels above 16 only with the profile and `--above-16-decision`. **The result bounds site-g only:** agent sandboxes stay up through model turns, so host memory at a level is a separate limit; each decision line's `host` shows it for the level (MemAvailable at start, minimum and end, and this level's sandboxes up, peak and mean, sampled every 5 s).

## M+ (`mplus.py`, `provision.py`, `placement.py`, `s2ranges.py`, `breakeven.py`)

Space `icsa2027_mplus_*`, supported by site-g and site-f, with the data uploaded to site-g and hashed from site-g against #3's manifests.

**The forbidden check, as implemented:**
1. Evict site-f's replica and confirm through `GET /data/{id}/distribution` that site-f holds nothing.
2. Provision.
3. Confirm the scope is placed, through the same API.
4. Confirm again from the sandbox's `replicate` hook, right before a fresh mount.

A transfer's reported status never counts as placement, because Onedata 25.0 can report `completed` for a replication that placed nothing or an eviction that removed nothing (prior-study issues 0003, 0006). If placement fails, the campaign stops; it does not measure.

**S2's required extent:** Onedata's transfer jobs replicate whole files only. So the byte ranges the pipeline's reader needs, traced on the local copy, are read through site-f's REST endpoint, which fetches them from site-g. Growth of site-f's replica during a later M+ run is recorded, so bytes the scope missed show up instead of passing as pre-placed.

**M cold, and the three rows of the report** (science, #12):
- **Primary:** M+ on site-f against M cold on site-f, a fresh mount from a confirmed-empty replica, so reads replicate on the fly from site-g. They alternate per instance in one window, since M+ runs during the campaign: a contended M+ is never compared with a quiet M cold.
- **Secondary, labelled "different conditions":** M+ on site-f against M cold on site-g, taken from step A's M runs (`mplus-report --site-g-dir`).
- **Scripted bound:** the same P and W, with C from M's runs in the WAN anchor, and no extra runs (`--wan-dir`).

**Break-even:** the smallest k >= 1 with P + kW <= kC, or none when C <= W. The interval is a seeded percentile bootstrap (`mplus-report`).

```
python -m icsa.scripted mplus-setup --out DIR --manifests DIR
python -m icsa.scripted mplus-measure --out DIR --space DIR/space.json [--instances I35,I37,I48,I01,I06]
python -m icsa.scripted mplus-report --out DIR --site-g-dir A_DIR --wan-dir WAN_DIR
python -m icsa.scripted teardown --out DIR --space DIR/space.json --providers site-g,site-f
```

**`teardown` follows the operator's rule (2 Nov), in `day0/scripts/odclean.py`:** it deletes the space's files through Onedata, checks that the space root lists empty and that `/volumes/posix/<spaceId>` is empty or missing on every supporting provider (read-only `find` and `du` through `dsk.sh`; the ssh key is on the dev host only), and only then revokes the supports and deletes the space. A space with files left, one already deleted, or one whose disk cannot be checked (no key, a provider with no kubeconfig such as site-e, an ssh failure) is not deleted and nothing is revoked: the command prints the refusal (space id, provider, size seen or "unknown") and exits 3. Remove nothing on a disk by hand; give the space id, provider and size to the lead, for the operator.

## WAN anchor (`wan.py`)

T, D and M from the off-site provider `site-c`, in an `icsa2027_wan_*` space supported by site-c only: S1 on I35, I37 and I48, then S2 on I35. Each REST request is timed client-side in the sandbox. M has the per-day read times, since a mount has no requests to time.

## Tests

- `uv run pytest -q tests/scripted`: the comparator, plans, cap rule, block maps, break-even and M+ control flow, against hand-computed values and a fake federation whose statuses lie as prior-study recorded. It also includes the script on the real local data against the frozen truth.
- `tests/scripted/test_sandbox_paths.py`: real sandboxes and the gate on the real bytes, served by the local mock. It needs `ICSA_SANDBOX_IMAGE`. M uses a stand-in directory there; real oneclient is only exercised by the runs on site-g.


## M+ report: the WAN rows

`breakeven.json` has `wan_runs` (the anchor's M runs per layout, each with its UTC time and wall) and `wan_note`: S2 may enter the scripted WAN bound along with S1, and off-site rates varied more than 20x between measurements, so each WAN figure is the link at that time. The campaign's background queue ends with a repeat of the site-c and site-e rate check near 02:00-03:00Z (`tools/scripted/rate_check.sh`, from the rate-check PR).
