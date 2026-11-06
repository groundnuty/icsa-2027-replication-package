# Blind code inspection of runs the instrument labels `unknown` (amendment 11)

**Decision:** the operator, 1 Nov 2026, about 20:05Z, before any agent run: two coders from different vendors read the code of `unknown` runs blind, and a label changes only if both agree.
**Why:** the analysed-extent instrument tracks data dependence through arrays, but not through Python's control flow or scalars. So a run that loaded everything required, and wrote its mask with ordinary loop code, comes out `unknown`. Without a remedy, go criterion 3 (at most 10% `unknown`) would very likely fail, and H1's bounds would be uninformative.
**Review:** two adversarial passes by Codex Astra (`reviews/inspection-rubric/`): draft 1 unsound; draft 2 sound with two changes, both applied here. The coders now **extract** the extent that reaches the saved mask, and a script compares it with the required extent, rather than the coders judging completeness themselves.

## 1. Which runs are inspected

| set | runs | purpose |
|---|---|---|
| **R: resolution** | every run the instrument labels `unknown` | resolves labels |
| **C: check, pilot** | every pilot and calibration run the instrument labels `complete` or `omitting` | measures the coders against an instrument they don't see |
| **C: check, main** | a seeded random sample of instrument-decided main runs: up to 15 `complete` and 15 `omitting` per option × layout | the same, on the main campaign |
| **K-test: known answers** | the cases of §6, written by the code agent, unseen by the science agent | the gate (§7) |

The sets are mixed into one queue in seeded random order. Nothing in a packet shows its set.

**The instrument is not infallible,** so disagreements on set C are investigated, never just counted. Set C skews towards vectorised code, so it measures the coders on the easier part of the population; this is stated.

## 2. Coders

- **Codex `gpt-6-astra`**, reasoning effort high, read-only sandbox.
- **Claude Opus 5.5 (`claude-opus-5-5`)**, adaptive thinking, effort high.

Each coder gets every packet in a fresh context. They work independently, with the same prompt (hashed and archived) and the same packet. Neither is a subject model. Opus shares a vendor with two subject models (Claude Haiku 5.5, Claude Sonnet 5.5), which is stated, and agreement is reported per subject model. Every packet and answer is archived for the artifact.

## 3. Packet

**Contents:**
- an opaque id;
- the task prompt exactly as the agent saw it;
- the run's code cells in order, each with its stdout and stderr truncated to 2,000 characters, keeping the first and last 1,000 so that tracebacks and the final lines survive;
- the list of files the run wrote, with their final sizes.

**Not included:**
- the agent's final report, and any self-assessment;
- the instrument's label, bounds or extents;
- option, model or set names as metadata;
- the hypotheses;
- any other run.

**Sanitised, with semantics kept:** run, scenario, directory and model identifiers in paths, comments and output are replaced by neutral tokens, consistently within a packet.
**Before use:** every rendered packet is scanned for residual cues (set or label words, scenario names, expected-answer assertions). A random 10% of rendered packets, K-test and real mixed, is read for cues by a reviewer who has not written K-test cases and will not see the coders' answers before the gate: a fresh Claude Sonnet 5.5 subagent in the code agent's session. It reports only cues found, not the cases' content. The science agent reads packets only after the gate.

**Unavoidable:** the access paragraph of the prompt, and the code itself, show the option.

## 4. What the coder extracts

The coder is told: *Identify the code path that produces the mask in the final saved output file. Report which sea-surface temperature values reach it.*

**A value reaches the mask** if it is an input to any operation on that path: arithmetic, a reduction (a percentile, a mean, a sum), a comparison, a selection, an index, a branch condition or a loop bound, whose results flow into what is written to the mask. **It does not need to change the result.**

**Dependence follows individual output elements:**
- Slicing credits only the selected source positions; passing a whole array into a narrow slice credits only the slice.
- A conditional selection (`np.where`, a masked choice, an `if`) credits the condition and, at each position, only the branch actually selected.
- Merely evaluating an operand doesn't establish that its values survive selection.
- Where the selected positions can't be established, answer CANNOT TELL for the affected part.

**Rules:**
- **Only the path to the saved mask counts.** Diagnostics, printed checks, unused results, attempts that are later overwritten, and files the final computation does not read do not count.
- **A printed value counts if the agent copies it into later code** on that path, for example as a literal. Then it carries what the printed value depended on.
  - A print is excluded only when the packet shows it isn't used.
  - If missing or truncated output keeps you from establishing whether later literals came from a printed calculation, answer CANNOT TELL for that dependence.
- **A value read back from a file the run wrote** carries what was written into that file, if the packet shows it. Otherwise answer CANNOT TELL for the affected part.
- **Where the code fails and falls back** (an exception handler, a default), judge what was actually saved.
- **Placement is not coverage.** A mask written at the wrong coordinates is a correctness error, not an omission: report source cells, not where results were written.
- **When unsure, answer CANNOT TELL.**

**The answer is structured; each part cites code lines:**
1. **Baseline:** for each year 1992–2002, the calendar days whose values reach the mask, as date ranges. Or "none", or CANNOT TELL for that year.
2. **Target:** the dates whose values reach the mask, or CANNOT TELL.
3. **Cells:** whether every sea cell of the region contributes its own values, or which cells don't (by rule or list), or CANNOT TELL.
4. **Exceptions:** any day or cell excluded inside a range, such as a skipped date, duplicate dates replacing others, or stride sampling.

## 5. Verdicts and the decision rule

**A script compares each coder's extraction with the required extent:**
- the region's sea cells;
- 12 May–20 Sep of each year 1992–2002;
- the 92 target days.

**Each coder's verdict:**
- **COMPLETE:** the extraction covers all of the required extent, with no CANNOT TELL anywhere.
- **OMITTING:** a definite part of the required extent is missing from it. The script names the missing parts.
- **CANNOT TELL:** otherwise.

**The rule for set R:** an `unknown` run becomes `complete` only if both coders' verdicts are COMPLETE. It becomes `omitting` only if both are OMITTING. Otherwise it stays `unknown`. A run is `omitting` when both say OMITTING, even if they name different parts. **The counterfactual decomposition is computed only when both coders' extractions agree exactly** and leave no part CANNOT TELL, since the registered rule needs the exact analysed extent. Otherwise it is reported as not computable for that run.

**Inspection never overrides the instrument.** An instrument `complete` or `omitting` stands, whatever the coders say on set C.

## 6. Known-answer set K-test

The code agent writes each case as plausible agent code, with neutral names and no assertions, and fixes the answer by construction. The science agent does not see the cases' code before the gate, and the rubric is not tuned on them.

**At least 32 cases, about half complete and half omitting. Most must route to instrument `unknown`,** so the coders' answers decide them. Each pattern with a complete and an omitting member is a pair:
- **Scalar and loop styles:**
  - the literal oracle (run boundaries and slice writes);
  - thresholds via `.tolist()`;
  - a full `.tolist()` pipeline;
  - a `nanpercentile` loop, with and without `float()`;
  - anomaly against zero;
  - `np.diff` run edges;
  - SciPy smoothing with the required margins.
- **Partial coverage inside groups:**
  - June–August of each baseline year, without the May and September margins;
  - one missing baseline day;
  - stride sampling;
  - duplicate dates replacing required days at the expected length;
  - different missing days in different cells.
- **Paths that don't reach the mask:**
  - a per-cell QC check beside a truncated baseline;
  - "quick against reference" with equal bounds, and with bounds differing by 1;
  - full-baseline diagnostics printed while detection uses 3 years;
  - a complete attempt overwritten by a truncated retry;
  - an exception fallback that saves an all-false mask;
  - a complete computation followed by a partial slice overwrite;
  - a stale file reused for the final save.
- **Indirect paths:**
  - printed thresholds copied as literals into the mask code, as one pair: used and ignored;
  - a scratch file reloaded, complete and partial;
  - a subprocess producing the mask.
- **Space:**
  - one sea cell skipped;
  - longitudes reversed on writing, with full coverage, which is complete;
  - a cell's values replaced by another's, which is omitting.
- **Options:** a matched subset of 3 complete and 3 omitting patterns through T, D and M, both layouts. T includes in-memory decoding.

**Forbidden check:** taking a case's answer from either coder's output, or adjusting a case after seeing the coders' answers.

## 7. Go criterion 3 under this procedure

**Every part must hold:**
1. **K-test, the coder pair's own answers against truth, for every case,** whatever the instrument says:
   - no omitting case answered COMPLETE by both;
   - at least 80% of the complete cases answered COMPLETE by both;
   - none answered OMITTING by both.
2. **K-test through the full procedure:** no omitting case ends `complete`.
3. **K-test by option:** parts 1 and 2 hold within each option's matched subset.
4. **Set C, pilot:**
   - no run answered COMPLETE by both coders while the instrument labels it `omitting`;
   - runs answered OMITTING by both while the instrument labels them `complete` are at most 10% of those runs;
   - every disagreement is investigated and reported.
5. **At most 10% of pilot runs are `unknown` after inspection.**

**If any part fails:** the rubric is revised, the revision is a dated amendment, and a fresh K-test set the revision hasn't seen is written before any main-run label is used.

## 8. Reporting and independent check

- **Primary H1 labels:** after inspection.
- **Sensitivity:** instrument-only labels, with the registered bounds.
- **Per option and model:**
  - the route mix: instrument-decided against inspection-resolved;
  - Cohen's kappa between the coders, also per subject model;
  - the coder pair's error rates on set C and on K-test, with intervals;
  - tokens spent.
- **Independent check of resolved labels.** Set C doesn't cover set R, so a seeded sample of inspection-resolved runs, oversampling resolved `complete`, is checked by a **dependence test by replay**, built during the campaign:
  - **Positive evidence:** perturbing a required group changes the replayed mask where the reference's mask changes. This shows that some values of that group are used, not that every required cell-day is.
  - **The opposite isn't proof:** no change is not taken as proof of omission.
  - If the replay isn't ready before the paper, this is stated as a limitation.
- **Stated limitations:**
  - models judging model-written code;
  - coders cannot be blind to the option;
  - set C skews towards vectorised code;
  - the extraction relies on reading code, not executing it.
