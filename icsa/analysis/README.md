# icsa.analysis — pre-registered analysis pipeline (#14)

Scored run records (`icsa.records.ScoredRow`, one per run) in; contrast tables, bounds,
pagination cell, instrument sensitivity, mixed models, power and exhibits out.

## Run

    uv run python -m icsa.campaign export-infra --out infra.json   # from the campaign store
    uv run python -m icsa.analysis.run --rows scored_rows.jsonl --infra infra.json --out results/analysis --overhead overhead.json [--causes causes.csv] --fidelity-rows adapter_rows.jsonl --inspection-labels labels.jsonl [--inspection-coverage coverage.jsonl] [--instrument-audit audit.json]

`scored_rows.jsonl` holds `dataclasses.asdict(ScoredRow)` per line (enums as their values).
`causes.csv` (optional) has `block,run_key,cause` for the coded causes. Output: CSV + Markdown
tables, `fig_outcomes.png`, `fig_causes.png` and `manifest.json` (config SHA-256, git
commit, whether HEAD is at a tag, whether the tree is dirty: from git, else from the snapshot's `.code-stamp.json`,
and `null`, never clean, when unknown; `code_version_source` says which).

## One config file

Every pre-registered constant is in `preregistered.toml`: alpha, smallest effects
(10 percentage points, factor 2), bootstrap B / level / seed, power seed and simulation
count, Wilcoxon options, contrasts, the analysed campaign blocks, the pagination primary seed,
the token definition, the placeholder instrument-error scenarios. `PLACEHOLDER` entries (pagination seed base,
placeholder scenarios) are settled before the freeze; the instrument-audit rates are NOT written here (see below).

## What enters the analysis

- **By block, never by instance id.** The primary analysis uses only runs whose `block` is `main`
  or `pagination` (`[blocks].primary`). The 10 pilot instances are 10 of the 50 main instances, so
  the main-block runs on them stay in; the `pilot` runs, the `calibration` block and the optional
  blocks are out. A run flagged `exclude_from_analysis` is out whatever its block, and a run
  of a block outside the list is out whatever its flag: either marker alone drops a row.
- A row **without a block is an error** (the scoring step must carry the run record's `block` and
  `exclude_from_analysis` into `ScoredRow`; `score_run` does). `rows_per_block.csv` and the manifest
  count the rows kept and dropped per block and reason (and the exhausted runs, as `exhausted_*`), so a misnamed block cannot vanish silently.
- The pilot's only use is the power re-estimate: `adapter.pilot_frame` -> `secondary.pilot_power`
  (`power_from_pilot.csv`: the pilot's between-region SD of the paired omission difference per
  contrast, and power at that SD).
- The fault-injection fidelity table comes from #11's scripted runs, which carry no campaign block:
  pass their `adapter_rows.jsonl` as `--fidelity-rows`. It leaves out flagged rows and the pilot,
  calibration and optional blocks (`[blocks].never`). Campaign rows always need a block. It keeps H3's
  cell, option x layout x record x condition, with a tested row over the faults observable by design and a
  reported row over all of them. A verdict needs the planned allocation, so it comes from `h3_table.csv`
  (`--h3-table`), which is joined on; the analysis stops if the two tables disagree.
- Coded causes (`--causes`, columns `block,run_key,cause`) join on `(block, run_key)`, because
  `run_key` alone is shared by a pilot run and the main run of the same cell.

## Labels after inspection (amendment 11, rubric §8, amendment 19(a) and (f))

H1's primary labels are those **after inspection**; the instrument-only labels (`label_raw`) are a sensitivity row
(`instrument_only_sensitivity`, which takes nothing from inspection: raw label, no label after inspection, no coverage from the coders).
- `--inspection-labels` (REQUIRED; an empty file says inspection has not run): one record per inspected run, `block`, `run_key`
  (`RunId.key()`), `label_after_inspection`, `route`, made from the inspection's `decisions.json` by
  `python -m icsa.analysis.inspection --decisions decisions.json --out labels.jsonl` (R-set packets only). The decisions' run keys must be the
  store's `<block>__<RunId.key()>` with the block equal to the packet's phase; anything else is refused.
- `--inspection-coverage` (optional): the coders' coverage where both extractions agree exactly, keyed the same way; every record needs a label record.
- `ScoredRow.label` stays the instrument's label after routing; `label_after_inspection` is set beside it, only on a run the instrument left
  `unknown` (an override of `complete` or `omitting` is refused). The analysis reads the primary label as `label_after_inspection` where set,
  else `label`, for every label outcome (omission, undisclosed, end-to-end); the coverage point of a run the instrument left unknown stays
  null unless the coders agree exactly; `routed_to_inspection` comes from the raw label and its reasons (the labeller's rule), so a routed run
  stays routed after inspection resolves it. The manifest's `label_sources` counts the primary-scope finished runs by where their label comes
  from (`instrument`, `inspection`, `unresolved`, `not_inspected`).

## The strict reading beside (amendment 36(d), `strict.py`)

36(c) made the mask parser read dims named `latitude` / `longitude` as `lat` / `lon`; the lenient reading is the verdict. 36(d): the registered strict
reading is reported beside every outcome it changes, per option x layout x model, with the count of masks read through the alias.
- `strict.strict_rows(rows)` turns each row with `mask_dim_alias` True into the row the scorer writes for a failed mask (unfinished, no label,
  correctness or report fields; the docstring lists each field and why). Rows with `mask_dim_alias` False or None (scored before 36) come back
  unchanged. It goes AFTER `inspection.apply` (inspection refuses a label for an unfinished run) and clears what inspection added to the run.
- Every table is the table the analysis already builds, run on those rows; no measure is written twice. The omission table is
  `secondary.denominator_table` itself, called per model and, for the pooled line, on all the cell's runs.
- `run_all` writes `strict_beside_finished_share`, `strict_beside_correctness` and `strict_beside_omission` (CSV + Markdown), next to the main tables, which
  do not change. One line per option x layout x model and, last in each option x layout, one `model` = `pooled` line over all its runs (the same code on all
  the runs, not an average of the models). Columns: `option, layout, model, N, n_alias`, then each measure followed by its `_strict` column. `N` is the cell's
  runs (`denominator_table`'s `N`), the same under both readings. `correctness` holds the registered outcomes only: `event_f1_mean` over `event_f1_n`,
  `false_alarm_rate` over `false_alarm_n`, `end_to_end(_rate)`.
- `tools/strict_beside_pilot_counts.py --rows scored_rows.jsonl --out counts.csv`: the finished-share table of the pilot block, counts only.

## H4: directions across models (descriptive, science, #14, 19:11Z)

No test. `h4_per_model_effects.csv`: each contrast's per-model effect with its region-bootstrap CI (the primary contrasts' own
resample) for every contrast outcome, plus bytes between sites on the log2 scale (as tokens; `effect_ratio` is the geometric-mean
ratio), per layout, and whether it agrees in sign with the pooled direction. `h4_directions.csv`: per contrast, the pooled effect and
CI, the models with an effect and those agreeing in sign (signs on the 12-decimal grid; a pooled 0 has no direction), and the
cheaper and the stronger tier side by side (`secondary.H4_TIER_PAIR`: claude-haiku-5-5, claude-sonnet-5-5, parameters.md's tier A).

## Infrastructure failures (parameters.md, "Infrastructure failures")

- `run_all(..., infra=...)` / `--infra` is **required** (keyword, no default; `None` is an error). It is the
  campaign store's export (`python -m icsa.campaign export-infra`, format `icsa-infra-export-v1`, written by
  `icsa/campaign/export.py`): `exhausted_runs`, `unfinished_runs` (pending or harness error), `discarded_usage`
  (tokens and wall time of `infra_fail` attempts per block x cell; `interrupted` attempts in their own columns) and
  `analysed_attempts`. All four lists must be present; `infra.InfraAccount.empty()` states there are none.
- A run whose 3 infrastructure attempts are used up has no outcomes and **leaves the primary denominators** (it is
  not a row). It is reported per cell (`exhausted_per_cell`), per option with the discarded attempts' usage
  (`infra_per_option`, primary blocks), and in `rows_per_block` as `exhausted_kept|flagged|block`. Pilot,
  calibration and flagged exhausted runs are out of the primary scope exactly like scored rows.
- **Sensitivity** (`exhausted_sensitivity_*`, column `sensitivity`): the exhausted runs of the primary scope count as
  time-capped (K) in the omission bounds and as failures (0) in the end-to-end outcome.
- Per-run outcomes use the first attempt without an infrastructure failure: a `ScoredRow` with `infra_failure`, or
  whose `attempt` differs from the export's analysed one, is an error; so is a run both exhausted and scored.

## Runs where the agent saw a data-path error (`flags.py`)

ONE concept in every option: **the agent saw an error on the data path, of any origin** (science, #7). Two definitions, in order:
- **A (preferred):** `ScoredRow.agent_saw_data_error`, the tracer's flag (#9), the same rule in every option. It is an explicit argument of `score_run(..., *, agent_saw_data_error=None)`, taken from `label_run`'s `flags["agent_saw_data_error"]` (or `analyse.data_errors_of(trace_dir)`); never from the sandbox record.
- **B (otherwise), from outside the agent**, carried by `score_run` into `ScoredRow.data_error_sources` from the run record's sandbox metadata:
  T, T-unpaginated, D: a 5xx or reset that reached the client, gate **or** upstream (`gate_transfers.errors`); M: a FUSE error the sidecar
  log summary (#61) marks `fuse_not_caused_by_agent` (`sidecar_errors`). **Errors the agent's own request causes are not counted:** the gate's
  client-origin errors (`client_request_errors`, e.g. a 404) and the FUSE errnos the summary calls agent-caused (`fuse_caused_by_agent`: ENOENT, EROFS, ...).
  EACCES and EPERM are not agent-caused there (an expired read-only token looks the same), so they flag. An unreadable sidecar log is *not available*.
- A wins over B. A run with neither source is **not available**: never 0, never clear.

A run is *flagged*, *clear* or *not available*. `agent_seen_errors`: per option the count and share of each, runs per definition
(`definition_A|B|none_runs`), and **descriptive** counts per origin (gate, upstream, sidecar, unattributed, agent-caused; B runs only; they never
drive the exclusion). `flagged_exclusion_contrasts`, `flagged_exclusion_pagination`, `flagged_exclusion_account`: the same contrasts without the
flagged runs, `sensitivity = excluding_flagged_runs`, the all-runs effect beside, and `definitions_used` (`A:n;B:n;none:n`) on every row and in the
manifest (`data_error_definitions`). Not-available runs stay in the sensitivity (the account counts them).

## Tokens of runs cut mid-request (amendments 26(d); `usage_flagged_runs`, `tokens_flagged_sensitivity`)

A run cut during a request counts at its completed requests' tokens, flagged (`usage_complete` False); `log2_tokens`, `input_tokens` and `output_tokens`
are NaN only for a run cut in its **first** request, which has no tokens (`first_request_cut`; no completed request on record, `ScoredRow.requests_completed`).
`usage_flagged_runs`: per option x layout x model, runs, flagged runs, the flagged share, and the first-request cuts. `tokens_flagged_sensitivity`: the
tokens contrast with `variant` = `primary`, `flagged_left_out`, or `flagged_at_upper_bound` (completed tokens plus the bound on the request that was cut,
input and output, from the run record: `ScoredRow.cut_request_input` / `cut_request_output`, set by the scorer with `icsa.cutrequest`, one token per byte; a
flagged row with no bound on record is left out of that variant), and `n_runs_left_out`, the flagged runs the variant does not count. The cost table carries
`usage_flagged_runs` and `first_request_cuts` beside its means.

## Wall time with the enforcement overhead (`overhead.py`)

Wall-time contrasts are **as measured** (`wall_time_contrasts_with_overhead`, `wall_time_with_overhead`); the scripted
enforcement overhead is stated beside them and **never subtracted**. `run_all(..., overhead=...)` / `--overhead` is
**required**; `OverheadTable.absent()` (or a file with an empty `rows` list) states it was not measured, and the tables
then say `overhead not measured` with an empty number, never 0. #12 emits (JSON, `icsa-enforcement-overhead-v1`):

    {"format": "icsa-enforcement-overhead-v1",
     "rows": [{"option": "T", "layout": "S1", "overhead_s": 1.8, "k": 5, "baseline": "no gate",
               "lo": 1.1, "hi": 2.6}, ...]}

One entry per option x layout measured; `overhead_s` = median wall time with the enforcement minus without it (seconds);
`k` >= `[overhead].min_k` (5) repeats per arm, else refused; `baseline` is `no gate` (T, T-unpaginated, D: gate vs no
gate) or `unsandboxed mount` (M: sidecar mount vs an unsandboxed one); `lo`/`hi` optional, both or neither. A cell
without an entry reads `overhead not measured`. Tokens, correctness and bytes are not touched.

## Cause breakdown (`cause_breakdown`, `--causes`)

Columns of #17's causes table used when present: `cause_detail`, `population`.
- `cause:<code>` rows keep the totals per bare cause; where `cause_detail` differs (`truncated_listing:client|agent`)
  extra `cause_detail:<detail>` rows split it.
- Runs with `population == incorrect_complete` are `incorrect_complete:<code>` rows, never merged into `cause:` rows.
- `recovered_from_truncated_listing` (`--cause-flags flags.csv`, #17's `flags_table()`): the recovery rate **over all analysed runs** per option
  (`recovered / (recovered + not recovered)`), with unknown (no value) and runs without a line in the table (`no_flag`) shown apart, never as
  false, and `listing_evidence_incomplete` counted per option beside it. Empty without the input.

## Instrument audit

Its rates are results of the study (they need agent runs) and enter **only the sensitivity analysis, afterwards**:
`--instrument-audit audit.json` (format `icsa-instrument-audit-v1`, per option x layout with optional intervals;
see `audit.py`, written by #35). Without it only the placeholder scenarios run; every row of
`instrument_sensitivity` has `rates_source`, and the manifest records `instrument_rates_source`.

## Pipeline

1. `adapter.rows_to_frame`: the only reader of `ScoredRow` fields.
2. `contrasts`: seeds -> instance -> region x model -> region, each a plain mean. Per arm, a region value is the mean of its defined instances (per model); the contrast is the
   difference of arms, and regions undefined in either arm are dropped and counted
   (`n_regions_dropped`). The pagination cell pairs by instance. Wilcoxon signed-rank on the
   25 region differences (zero differences are dropped, as `zero_method = "wilcox"` says, and
   their number is reported per contrast as `n_zero_dropped`; differences below `zero_tolerance` are
   float noise and count as zeros, and the rest are rounded to 12 decimal places, `contrasts.snap`, so differences
   equal in arithmetic tie whatever the order of summation), Holm over the 3 contrasts within each outcome x layout, 95%
   region-cluster bootstrap (one region resample shared by all models; equal model weights),
   per-model effects and directions. `counts_for_guide` = Holm p < alpha and |effect| **at least** the smallest effect
   (`at_least_smallest`: |effect| >= 0.10 for omission and coverage, |log2 ratio| >= 1 for tokens, both rounded by `snap`,
   so an effect exactly at the smallest effect counts; science, #14, 19:11Z, from the registration). Event F1 has none, so it is NA. Coverage is two outcomes, `coverage_baseline` and
   `coverage_target`, never combined: each has its own Holm family and the 10-point smallest effect.
3. `secondary`: denominators and bounds, pagination cell (T-unpaginated minus T on S1; T
   restricted to the primary seed, all seeds as sensitivity), instrument-error correction,
   mixed models (`option * layout + (1|region) + (1|model)`), power by simulation.
4. `exhibits`: level figure with intervals, cause breakdown, cost table, fault-injection table.
5. `sim`: the simulator used by the tests. Independent of the pipeline; true effects are inputs.

## Freeze

Run the tests, then tag the merge commit **before** the main runs (this is the parent's job):

    uv run pytest -q tests/analysis
    git tag -a analysis-freeze-v1 -m "analysis pipeline frozen before main runs; config sha256 $(sha256sum icsa/analysis/preregistered.toml | cut -d' ' -f1)"
    git push origin analysis-freeze-v1

Record the tag and the config SHA-256 in the run manifest. After the tag, any edit to
`icsa/analysis/` or to `preregistered.toml` is a deviation to be disclosed.
