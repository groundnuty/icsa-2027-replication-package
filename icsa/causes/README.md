# icsa.causes: omission-cause coding (#17)

    from icsa.causes import evidence_from, code_runs, write_sheet, kappa_report
    batch = code_runs(evidence_from(record, scored, required, analysed=lab.analysed, read=lab.read.extent,
                                    listing_disagrees=lab.analysis.flags["listing_disagrees"], ...) for ...)
    batch.table().to_csv("causes.csv")        # block, run_key, cause (+ secondary, attribution, cause_detail, population, trail)
    write_sheet(batch, "sheet/")              # sheet.csv + codebook.md for the second coder, key.csv stays here
    kappa_report(key, batch.table(), filled_sheet)   # Cohen's kappa + bootstrap CI, overall and per option

Codes, rules and precedence: `codebook.py` (the text shipped to the second coder). Rules: `rules.py`.

- **Population.** Finished runs the instrument (#9) labels `omitting`; every unfinished run; finished
  `complete` runs whose result is wrong (`analysis_error_on_covered_data`). Finished `unknown`-label runs
  are not coded: `Batch.skipped_counts()` reports them.
- **Inputs** are plain evidence (`RunEvidence`), built from the #8 record, the #13 row, the required extent
  and #9's labeller output (`analysed` = A_lo, `read` = the read extent, `listing` = per-directory
  `DirListing.to_json`, `read_beyond_units` = `ReadExtent.beyond`). `None` always means "not observed".
- **`truncated_listing`** (renamed from `unfollowed_pagination`): fires only if a listing was truncated, a required
  day lies beyond the listed names (S1 names sort in day order), **and the run read no data file beyond
  the union of the names it was listed** (the beyond-the-names clause alone is true of every required day:
  the first 1,000 entries end on 1984-09-26, the first required day is 1992-05-12). A run that read beyond
  them escaped the truncation and is coded by the other rules. Attribution `client` unless a request
  carried a page token; an agent that stops after its first page cannot be told from the client in the
  request log and is attributed `client`.
- **`recovered_from_truncated_listing`** (flag, every run incl. complete ones; True/False, None when the
  S1 listing or read extent was not observed): truncated listing and a read beyond the listed names.
  Columns of `cause` rows and `Batch.flags_table()` (all runs). Units read outside the required days are
  a count unless `read_beyond_days` gives their days (counted with the required-day reads against the listed names); with a count and no days, and no placed read beyond the names, the flag is None and
  `truncated_listing` does not fire and the run is counted as `listing_evidence_incomplete` (`Batch.listing_evidence_incomplete_count()`, `flags_table()`, CLI output).
- **`skipped_or_partial_read`** (was `..._download`): one rule for every option; `truncated_downloads` is
  D's sub-case (noted in the trail).
- **`incorrect_complete`** is reported as its own breakdown (`Batch.breakdowns()`), never merged with the
  omission causes.
- **Table for #14 `--causes`:** `block`, `run_key`, `cause` (the bare code). `cause_detail` is
  `truncated_listing:client` / `:agent` for a breakdown that needs the attribution.
- **Second coder:** human or model, same sheet. `sampling.model_coder_prompt` builds the model's prompt
  from one sheet row and the codebook. The sample is stratified by option x layout x primary code, 20%
  (at least one run per stratum). The sheet holds no code, no stratum column and no run key; rows are shuffled.
- **κ:** on the primary code; seeded percentile bootstrap CI over runs; NaN where chance agreement is 1.

CLI: `python -m icsa.causes {code,sheet,kappa} ...` (evidence from `evidence.write_evidence`).
Tests build every expected cause by hand from the #11 fault scripts and the #9 listing scripts.
