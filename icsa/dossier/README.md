# Pilot go/no-go dossier (#18)

    uv run python -m icsa.dossier CONFIG.json OUT.md

`CONFIG.json` names every input explicitly (paths relative to the config); nothing is found by scanning or by recency.
Keys: `equivalence`, `validation_189`, `ground_truth_record`, `instruments_summary`, `instruments_caveat` (text),
`scored_rows` (JSONL of ScoredRow), `run_records` (JSONL of RunRecord dicts), `live_classes`, `fault_cells`,
`scripted_pipeline`, `scripted_timing`, `planted_faults`, `pilot_inspections`. An omitted or unreadable input is MISSING. A JSON input with `"stub": true`
is MISSING too, never PASS. Overall: all six PASS, else NO-GO if any FAIL, else INCOMPLETE.

| criterion | input | format | gate (source) |
|---|---|---|---|
| 1 | `equivalence` (reports/refdet/octave_equivalence*.json) | list of blocks with `c1_pass`..`c4_pass` | all pass in >= 6 blocks (SCOPE.md); the 189-event comparison (`validation_189`) is reported, not gated |
| 2 | `instruments_summary` (#9 `summary.json`) | #9 format, **plus the re-validation fields** | every failure list empty; all five options have runs; **gated on the re-validated run**: the summary must carry `baseline_window: "method"` (the ruling's 12 May..20 Sep window), `data_kind: "compressed"` (deflate data) and `gates: "local-sim+real-confirmed"` (the #9 ruling of 1 Nov: the full matrix on the local path plus a real-path confirmation set on site-g), and a `real_confirmation` result `{"runs": <int > 0>, "differences": []}` with no label or analysed-extent difference from the local path; else MISSING (the short-baseline summary lacks them, and any difference keeps it MISSING until explained and fixed) |
| 3 | summary + `planted_faults` + `scored_rows` + `pilot_inspections` | see below | truth independent of the instrument. Scripted: omission known by construction (summary `by_true_label`, `omitting_called_complete`; planted `true` labels), re-validated summary only. Pilot: all 30 agent runs inspected by code reading; an omitting verdict on a complete label FAILs; a missing, null or undecidable inspection is MISSING. Unknown share <= 10% per option and pooled (label-based). The label vs `complete_extent` mismatch is a diagnostic line only |
| 4 | `live_classes` (LIVE_CLASSES.json), `fault_cells`, calibration start (earliest `started_at` of `run_records` block `calibration`) | h3_table rows (`option, layout, record, condition, n_faulted, n_control`) | every unknown_until_live cell classed; every live `recorded_at` before the first calibration run (none known: MISSING); per option x record at least one complete cell (>= 60 faulted and >= 30 fault-free), none: FAIL, no rows: MISSING. `meets_h3` (the full matrix) is reported, not gated |
| 5 | `scripted_pipeline` | STUB FORMAT (#12 not landed): `{"cells":[{option,layout,completed,correct}]}` | all five options x two layouts completed and correct |
| 6 | `scripted_timing` | the #12 emitter's format (`icsa-scripted-timing-v2`): `{"cells":{"T__S1":{single_run_wall_s, provider_io_bytes, curve:[{concurrency, wall_s, errors, within_disk, oom_kills}]}}, "blocks":{"1":{cap, wall_at_cap_s, cells}, "2":{...}}}` | the cap is PER BLOCK (science, #12, 1 Nov 17:30Z): block 1 = T, T-unpaginated, D, M in S1; block 2 = T, D, M in S2. Each block's cap is recomputed from that block's cells only (highest level with every cell <= 1.25 x its single-run wall, no errors, no OOM kill, within disk) and must equal the declared one; the declared `wall_at_cap_s` must equal the recomputed worst wall at the cap. A stub, absent or old single-cap format is MISSING. Term (b) of the time cap is the larger of the two blocks' walls at their caps |

Rule values (`rules.py`) come from RunRecords of blocks `pilot` and `calibration`, finished or not, infra-failed
attempts included: `TURN_CAP = ceil10(max(40, 2 x max tool rounds))`, `TOKEN_BUDGET = ceil10000(3 x max total tokens)`,
`TIME_CAP_MIN = ceil10min(2 x max(max wall, max scripted wall at the cap))`. Missing term (b), incomplete usage,
absent calibration runs and provisional-cap hits are printed as notes: the value is then not final.
Total tokens = sum of input + output tokens per turn (cached input is taken as counted in `input_tokens`: unverified).

Config values for design defaults the science agent must confirm: `unknown_share_max` (default 0.10, issue #18),
`include_infra_failed` (default false: infra-failed attempts are left out of the rule-value maxima, parameters.md line 38).

## New input formats (stubs until the producers land; a `"stub": true` file is MISSING)

`none_counts` (the pilot's per-option None counts; written by the pipeline lane; criterion 2 stays MISSING while any is non-zero, absent or a stub, #9 ruling 1 Nov 16:56Z):
`{"none_counts":{"T":{"runs":n,"read":k,"read_beyond_days":k,"listing":k},"T-unpaginated":{...},"D":{...},"M":{"runs":n,"read":k,"read_beyond_days":k}}}`, k = runs of that option whose field is None.
`read` and `read_beyond_days` are required to be 0 in every pilot option, M included; `listing` only for T, T-unpaginated and D (M lists with `os.listdir`, whose extent the tracer records differently, so M's `listing` key is not checked). M+ is not in the pilot.
The summary's own `real_confirmation.none_fields` (list of field names left None on the real runs) must be present and empty as well.

`planted_faults` (#11, truth = the planting script's expectation, never the instrument's label):
`{"runs":[{"case": str, "true": "omitting"|"complete", "label": the instrument's label}]}`.

`pilot_inspections` (#35's audit output, one entry per pilot agent run, blind to the label):
`{"format":"icsa-pilot-inspections-v1","inspections":{"<instance_id>|<option>|<layout>|<model>|<seed>": {"truth":"omitting"|"complete"|"undecidable"|null}}}`.
#35's verdict files are keyed by packet id (`icsa-audit-verdicts-v1`); the packet-to-run key map must be exported
into this format by #35 (interface not yet landed there). The pilot must have 30 agent runs; each needs a decisive verdict.
Every criterion reading a stub, absent, null or incomplete input is MISSING, never PASS.
