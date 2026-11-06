# Final results, and how to reproduce each

The final results of the study, organised by what the paper reports. Everything comes from the final snapshot at `results/analysis/final-20261106T0900Z/` (snapshot time 6 Nov 2026 09:00Z, all seed-1 runs) and its sensitivities at `results/analysis/final-20261106T0900Z-sens/`. Coding data are under `results/coding/`.

**Options:** the data use T, D, M and T-unpaginated for the paper's A (API), D (download), M (mount) and A+ (API with a complete listing). A − M in the paper is the `T-M` contrast in the tables.

**Primary tables:** `out-kaug/` and `out-coded-kaug/`, as `PRIMARY.json` names them. These are the frozen pipeline's tables with 6 runs counted as time-capped by rule: their earliest analysable attempt ran past the time cap, and was marked an infrastructure failure only because its record couldn't be read. `out/` and `out-coded/` are the same pipeline without that correction. **`make check` regenerates every table in all four directories byte for byte.**

**Scripts in `scripts/`** take the snapshot directory as their first argument:
- `gen_final_tables.py`: the paper's tables;
- `final_numbers.py`: every figure, the per-run ones from the coded rows in the snapshot's `h3/scored_rows_coded.jsonl`;
- `hyp_table.py`: the contrasts by the registered decision rule;
- `power.py`: power, which needs scipy.

They print text and write nothing. Run them from the package root, for example `python3 scripts/final_numbers.py results/analysis/final-20261106T0900Z`, and `power.py` with `uv run python`. On this package they print what they print on the snapshot before anonymisation, apart from the snapshot's own path and, at the end of `final_numbers.py`, the list of side files present, some of which this package does not ship.

## 1. Runs

2,442 scored runs, 2,103 finished, 7 models. Endings: report 2,256, token budget 111 (all one model, Qwen3-Coder), time cap 47, output cap 26, turn cap 2. Source: `out-coded/pipeline/scored_rows.jsonl`; cell counts in `out-coded-kaug/tables/denominators.csv`.

## 2. Completeness and correctness (Table VII)

Region means of model means; omission over finished runs labelled complete or omitting.

| Layout | Option | Omission [95%] | O/(O+C) [bounds] | Undisclosed | Event F1 | IoU ≥ 0.9 | End-to-end | F1 lost to omission / computation |
|---|---|---|---|---|---|---|---|---|
| S1 | A | 0.141 [0.107, 0.174] | 0.13 [0.12, 0.20] | 0.11 | 0.961 | 0.90 | 0.68 | 0.000 / 0.003 |
| S1 | D | 0.163 [0.116, 0.212] | 0.15 [0.14, 0.18] | 0.14 | 0.970 | 0.89 | 0.68 | 0.005 / 0.002 |
| S1 | M | 0.154 [0.116, 0.194] | 0.14 [0.13, 0.23] | 0.14 | 0.960 | 0.90 | 0.66 | 0.005 / 0.014 |
| S1 | A+ | 0.152 [0.112, 0.191] | 0.12 [0.11, 0.18] | 0.11 | 0.946 | 0.89 | 0.71 | 0.004 / 0.011 |
| S2 | A | 0.174 [0.132, 0.217] | 0.16 [0.15, 0.21] | 0.15 | 0.934 | 0.87 | 0.70 | 0.001 / 0.012 |
| S2 | D | 0.201 [0.156, 0.247] | 0.17 [0.16, 0.23] | 0.17 | 0.930 | 0.87 | 0.69 | 0.000 / 0.028 |
| S2 | M | 0.197 [0.149, 0.246] | 0.17 [0.16, 0.23] | 0.16 | 0.937 | 0.87 | 0.65 | 0.000 / 0.009 |

**Sources:**
- omission and F1: `out-coded/tables/levels.csv`;
- O/(O+C), bounds, undisclosed and end-to-end: `out-coded-kaug/tables/denominators.csv`;
- IoU ≥ 0.9: the coded per-run rows (`final_numbers.py`);
- F1 lost: the mean of 1 − `cf_omission_f1` and 1 − `cf_computation_f1` over replayed runs in `results/coding/coder_replay/coder_replay.csv`.

**A+'s omission and F1** use the same averaging over the coded rows (`final_numbers.py`). That averaging reproduces `levels.csv` for A and M exactly.

**Numbers in the text:**
- **omitting:** 299 of 2,103 finished runs (14.2%);
- **edge day only:** 190 of 299 miss only an edge day of the baseline window;
- **undisclosed:** 278 of 299 reported themselves complete;
- **false alarms:** 13 of 337 finished runs on event-free instances;
- **edge-day effect:** in 212 runs whose only shortfall is baseline edge days, no detected event changed. The largest threshold shift was 0.02 K for one edge day per year, and at most 1.3 K in the 22 runs with wider gaps (`results/coding/coder_replay/coder_edge.csv`).

## 3. Contrasts between options (Table VI, Fig. contrasts)

Paired by region, Holm-adjusted across the three pairs in each layout. A difference counts for the decision guide only if Holm-significant and at least the smallest effect: 10 points for omission or coverage, a factor of 2 for cost. Source: `out-coded-kaug/tables/contrasts.csv`, run through `hyp_table.py` or `gen_final_tables.py`.

| Outcome | Layout | A − D | A − M | D − M |
|---|---|---|---|---|
| Omission, pp [95%] (Holm p) | S1 | −2.1 [−7.1, +2.7] (1.00) | −1.5 [−5.4, +2.1] (1.00) | −0.6 [−4.6, +3.3] (1.00) |
| | S2 | −1.6 [−7.1, +3.8] (0.97) | −1.9 [−7.2, +3.0] (0.97) | −2.6 [−8.2, +3.2] (0.87) |
| Coverage of target, pp | S1 | −2.0 [−5.7, +1.8] (0.57) | −3.3 [−6.8, −0.2] (0.43) | −0.9 [−3.9, +2.7] (0.57) |
| | S2 | −3.2 [−7.8, +0.9] (0.37) | +0.5 [−3.0, +3.9] (0.91) | +3.6 [+0.5, +6.7] (0.12) |
| Event F1 | S1 | −0.010 (1.00) | +0.001 (1.00) | +0.004 (1.00) |
| | S2 | +0.002 (0.92) | −0.008 (0.92) | +0.003 (0.92) |
| Tokens, ratio | S1 | ×1.01 (0.49) | **×1.28 (0.002)** | **×1.27 (0.013)** |
| | S2 | ×1.11 (0.19) | ×0.93 (0.52) | ×0.84 (0.089) |

**No omission, coverage or F1 contrast is significant, and every omission interval lies within ±8.2 points.**

**A against A+ (single tests, `pagination_primary.csv`):**
- omission −0.4 pp [−5.0, +4.4], p = 0.98;
- coverage of target −4.6 pp [−7.7, −1.9], p = 0.007;
- event F1 +0.001, p = 0.96;
- tokens ×1.26 [1.13, 1.41], p = 0.001.

**Bytes between sites, a test added after seeing the data,** on the units with A, D and M all measured (`side-added-after-data/bytes_contrast_measured_units.csv`; ratio = 2^effect):

| Layout | A / D | A / M | D / M |
|---|---|---|---|
| S1 | ×0.71 (p = 0.19) | ×0.48 (0.13) | ×0.68 (0.24) |
| S2 | ×0.60 (0.037) | ×0.64 (0.064) | ×1.08 (0.52) |

## 4. Per model

Omitting finished runs: Gemma 103, Qwen3-Coder 91, Qwen3.8 60, GLM 28, Claude Sonnet 9, DeepSeek 6, Claude Haiku 2, from the coded per-run rows. Per-model directions are in `out-coded-kaug/tables/h4_directions.csv`.

## 5. Causes of omission (Fig. causes)

Finished omitting runs, by cause:

| Layout | Option | Baseline window short | Skipped or partial read | Truncated listing | Other or unassigned |
|---|---|---|---|---|---|
| S1 | A | 19 | 7 | 5 | 4 |
| S1 | D | 33 | 1 | 5 | 4 |
| S1 | M | 32 | 3 | 0 | 3 |
| S1 | A+ | 27 | 3 | 0 | 4 |
| S2 | A | 32 | 10 | 0 | 6 |
| S2 | D | 42 | 3 | 0 | 7 |
| S2 | M | 31 | 10 | 0 | 8 |

**Sources:** `results/coding/coder_replay/coder_causes.csv` (the window rule, else the codebook cause) for runs the coders resolved, otherwise `out-coded/pipeline/causes.csv`, which also holds the unfinished runs' causes.

## 6. Cost (Table VIII)

| Layout | Option | Tokens, median (k) | Wall time, median (min) | Bytes between sites, mean (GB) |
|---|---|---|---|---|
| S1 | A | 291 | 34.5 | 2.30 |
| S1 | D | 313 | 30.3 | 2.13 |
| S1 | M | 221 | 50.7 | 2.40 |
| S1 | A+ | 232 | 36.4 | 2.57 |
| S2 | A | 137 | 24.5 | 20.17 |
| S2 | D | 133 | 23.5 | 6.13 |
| S2 | M | 177 | 22.5 | 15.66 |

**Sources:** tokens and bytes from `out-coded/tables/cost_table.csv`. Wall time and bytes cover the runs whose bytes were measured, which is the environment that ran every option. The wall-time medians come from the per-run rows (`gen_final_tables.py`).

## 7. Validity of the reference and the labels (Table VI, checks)

**The reference:**
- **same events and dates as the catalogue authors' code:** 154 of 154 on identical input, with identical onset and end dates (`results/reference-validation/octave-domain/RESULT.md`, `domain.json`; made by `octave_domain/`);
- **published events both match exactly:** 21 of 189; 179 of the 189 overlap an event (same file);
- **a scripted program written from the prompt, with no model, reproduces the reference:** 240 of 240 cells, all 50 instances in S2 and 10 in S1, through each of the four data paths (`results/validation/oracle-table.csv`).

**The labels:**

- **coder agreement:** 1,967 of 2,058 packets, 95.6% [94.6, 96.4] (`results/coding/inspection/pair_kappa.csv`, rows R+C);
- **replay,** labels whose result matches the reference exactly:
  - complete: 1,268 of 1,344, 94.3% [93.0, 95.5];
  - omitting: 0 of 183 (`coder_replay.csv`, `f1_extent` ≥ 0.99999);
- **second coder:** κ 0.79 on 88 rows; 0.65 on the 60 not decided by how the run ended; 0.92 counting either code in the one case the codebook gives to two codes (`results/coding/inspection/second_coder_kappa.json`; recompute from `results/coding/second_coder/key.csv` and the answers beside it);
- **known answers:** 0 of 54 omitting cases called complete by both coders, for both coder pairs (`results/coding/k/`);
- **human readers:** 18 of 18 decided runs agree with the coders (`results/coding/coder_check/coder-check-answers.csv` against `coder-check-key.json`).

Intervals are Wilson 95%.

## 8. Fidelity of the platform's record (Table IX)

**Injected omissions** (`exhibits/fidelity_per_fault_type.csv`):
- **every fault type a record can observe by design: recall 1.00 / precision 1.00** on the injections with a usable result;
- **unobservable by design:** header-only reads are unobservable under A in S1 and under D; full read with partial use is unobservable under every option;
- **the audit log is not testable in S2.**

**A and D in S1 are incomplete,** as some planned injections left no usable result, most of them listing truncations planned with zero reads. Worst-case bounds (`fidelity-extra/fidelity_worstcase_bounds.csv`), counting each such injection as a miss:
- A: recall 0.81 (audit log) and 0.83 (access log);
- D: recall 0.81, precision 0.97 (audit log), and 0.83 (access log).

**In agent runs** (registered, model-weighted; flagged and omitting / flagged, not omitting / missed):

| Option | Layout | Access or per-read record | Audit log |
|---|---|---|---|
| M | S1 | 3 / 0 / 35: recall 0.07, precision 1.00 | 3 / 0 / 32: recall 0.08, precision 1.00 |
| A | S2 | 10 / 0 / 38: recall 0.14, precision 1.00 | not testable |
| D | S2 | 0 / 0 / 52: nothing flagged | not testable |
| M | S2 | 10 / 0 / 39: recall 0.16, precision 1.00 | not testable |

These come from the per-run record measures in the snapshot (`final_numbers.py`). A and D in S1 aren't reported.

**Self-report** (pooled; from the coded per-run rows): recall A 0.11, D 0.05, M 0.05, A+ 0.09; precision 1.00 for each.

## 9. Pre-provisioning (M+), measured by script

5 instances per layout, against cold reads through the mount at the agent's site:

| Layout | Provisioning, median | Data placed | Cold read | On placed data | Pays off after |
|---|---|---|---|---|---|
| S1 | 43 s | 0.50 GB | 453 s | 409 s | 2 analyses |
| S2 | 11 s | 0.53 GB | 52 s | 38 s | 1 analysis |

- **Time to first compute is unchanged:** 12.7 against 12.6 s in S1, and 6.9 against 6.7 s in S2.
- **Against A's and D's cold scripted analyses** (3 instances, an earlier step, added after seeing the data): **in S1, A's and D's 276–280 s beat M+'s 409 s, so M+ never pays off; in S2 it pays off after 1–2 analyses.**

Sources: `results/mplus/summary_table.json`, `results/mplus/breakeven.json` and the run's log `results/mplus/mplus_log.jsonl`; against A and D, `results/mplus/against-A-and-D/`.

## 10. Enforcement overhead

Measured by script in S2 only, 5 interleaved pairs per option, one run at a time on a quiet host, not at the campaign's concurrency:
- A: +0.2 s [−1.6, 2.1];
- D: +26.7 s [25.6, 28.3] (114 s against 87 s);
- M: +0.4 s [−1.5, 1.7].

S1 wasn't measured. Source: `out-coded-kaug/tables/wall_time_with_overhead.csv`, which `make check` regenerates.

## 11. Power

**The registered simulation:** 0.99 at a between-region SD of 10 points, 0.75 at 15.

**With the final data's own spread,** the estimated power for a 10-point omission difference, at Holm's first-step level:

| Layout | A − D | A − M | D − M |
|---|---|---|---|
| S1 | 0.75 | 0.97 | 0.99 |
| S2 | 0.80 | 0.89 | 0.80 |

Reproduce with `uv run python scripts/power.py results/analysis/final-20261106T0900Z`, which reads the coded per-run rows. The conclusions rest on the intervals in section 3, which exclude 10 points.

## 12. Sensitivities

Under `final-20261106T0900Z-sens/` (`out-retries`, `out-lab504`, `out-050`), against the frozen tables:
- the retries counted in place of the 6 runs counted as time-capped;
- runs retried after an endpoint's gateway timeout left out;
- the registered 00:50Z cohort cut.

**Tokens in S1 stay significant in all three:** A / M ×1.27–1.28 and D / M ×1.25–1.27. **No event-F1 contrast becomes significant.** These sensitivities don't carry the coders' labels, so they don't test omission.

**Not a result:** `side-added-after-data/extent_account_differs.csv` shows nearly every run as "differs", because the agents' reports rarely state an extent in a form that can be compared, so the day differences are null. It doesn't show that agents claimed more than they analysed, and the paper doesn't use it.

## Per-run figures

**The figures from the coded per-run rows** (IoU, edge-day counts, self-report, false alarms, per-model counts, A+ means, power) come from `h3/scored_rows_coded.jsonl` in the snapshot's folder: the scored rows joined with the coders' labels. `final_numbers.py` and `power.py` read it by default.
