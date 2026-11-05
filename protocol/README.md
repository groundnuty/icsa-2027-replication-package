# Protocol texts (science-owned)

The science agent owns these files; the code agent consumes them. Nothing here states hypotheses or expected directions: they are kept away from implementers on purpose.

| File | Content | Status |
|---|---|---|
| `task-prompt.md` | The task prompt template, identical for every option except one access slot | draft; the method paragraph waits for the estimator answer in #4 |
| `access/*.md` | The text for the access slot, per option | draft; unblocked by #10 item 3 |
| `report-spec.md` | The schema of the two output files, the validity rule and the disclosure rule | ready for review |
| `parameters.md` | Frozen values, and the rules that set values from the pilot | ready for review |

**Merging is not freezing.** Merged texts are drafts the code agent builds against. The freeze is the OSF registration before the pilot, with an anonymised view-only link.
- At the freeze, the static slots are filled (from #4, #5, #7 and #10), together with the rules for every pilot-derived value.
- The pilot runs with the provisional caps.
- The cap values are added afterwards by a dated amendment.
- Instance slots are filled per run.
- Parameters set from the pilot are registered as **rules**. Their values are added afterwards as a time-stamped amendment.
- After the freeze, any change is a new, dated amendment file. Frozen text is never edited in place.

## Deviations from the proposal (all acknowledged by the operator, 1 Nov)

The numbering matches the registration's "Deviations" section.

1. **Reference rule (triggered on 1 Nov by the #4 evidence).** The ground truth is computed by the frozen method from the S1/S2 values the agents read, not from the published threshold fields (`parameters.md`).
   - **Why:** the authors' SST, rebuilt from their event maps, differs from today's product version 202506 by a mean absolute difference of 0.26–0.32 K on published heatwave cell-days (maximum 2.85 K, checksum-verified files). Copernicus documents the June 2025 release as a full reprocessing (ESA SST_cci v3.0, a new under-ice value, a new land mask), after the catalogue's download. 7,019 cells that are NaN in the published fields are finite in 202506.
   - **Validation:** equivalence with the authors' code under GNU Octave, on identical data, in six blocks (within 1 float32 ULP; #4). Agreement with the 189 published events is reported as description of the data-version effect, not as a pass condition.
   - **Sea cells** are those with finite SST on every target day, a study adaptation of the authors' bathymetry mask, so that agent and reference agree by construction.
2. **Lossless compression (operator decision, 1 Nov).** S1 and S2 are stored as `float32` with deflate (level 4), not uncompressed. About 72% of each field is land (NaN). Measured: 12.1× smaller. File count, the single-file S2, and the D-versus-T/M byte ratio (about 3.6× in S2) are unchanged, and the values are identical for every reader. The proposal's "about 40 GB uncompressed" becomes about 4 GB.
3. **On-site data provider plus a WAN anchor (operator decision, 1 Nov).** Off-site site-ay providers deliver only about 10 Mbit/s to the run host (a lossy inbound site-ax path; #10 evidence). The agent runs therefore read from an on-site provider on a separate cluster. Every read still crosses the network to a separate Onedata provider, but latency is LAN-like. A scripted T/D/M measurement from the off-site provider `site-c` anchors the cost claims for WAN latency. The proposal's "at one remote provider, and the agent works at another site" becomes "at a separate provider cluster".
4. **Calibration set.** 42 extra agent runs (7 models × 3 options × 2 layouts × 1 instance), used only to set caps fairly across models and layouts and excluded from all analyses. The proposal's run matrix has none.
5. **Run order and drop order** (`parameters.md`). The proposal dropped the pagination cell first. It is now protected, because v13 makes it the evidence for a named remedy. S2 is reduced to three models first.
6. **Correct means cell-day IoU ≥ 0.9,** not F1 ≥ 0.9. With few events per instance, F1 moves in large steps; IoU scales smoothly. Event F1 stays a primary outcome.
7. **H3 tested against two records (approved by the operator, 1 Nov).** Day 0 showed that no default Onedata record holds byte ranges. Each option is calibrated against the default record (the file-access audit log) and a switched-on one (a Traefik access log with `Range` for T and D; oneclient's per-read log for M). The proposal expected block-level detection from the audit log alone. H4 therefore covers H3's agent-run measures only, since the fault-injection part uses no models.
8. **The required extent is what the method needs for the target,** not the whole baseline: for June–August, 12 May–20 Sep of each year 1992–2002, 1,452 days (ruling of 1 Nov on #9). Thresholds computed from these days alone are bit-identical to those from the full baseline on the target days (#5), so an agent analysing exactly these days is complete.
9. **Clients read directly from the data provider,** so no on-the-fly replication occurs under T, D or M; M+ alone replicates, in its own space. Day 0 showed that replication adds no transfer record and would blur the bytes each option moves.
