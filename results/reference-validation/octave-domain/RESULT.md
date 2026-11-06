# The authors' code over the whole domain on 202506, against the reference (#34 item 9)

Totals, not by option. Criterion and expectation were fixed in `octave_domain/PREREG.md` before the run (sha256 6d4a0d22...). Nothing was tuned.

## Run

- Input: BALarea (170,171 cells), 202506 S1, 1982-01-01..2023-12-31 (15,340 days), packed from the site-a master copy `dataset.tar`. Each of the 15,340 daily files was hashed as read and equals `data/manifest/s1_sha256.txt` (identical, line for line, to the master copy's manifest). The packed cells equal part 1's block inputs bit for bit on south, oslo, bothnian, archip, y1982 and the full-record round-trip block (`logs/verify_pack.log`).
- Code: the authors' Step_2 call as written (`detectc` of m_mhw a7bdda7 with part 1's patch and shims; patched `detectc.m` sha256 3c35ac02..., `provenance/PROVENANCE`), detection 1982-01-02..2023-12-30 (15,338 days), baseline 1992-2002. GNU Octave 9.2.0, one Apptainer SIF (sha256 d416cb41...) built from the `docker save` archive of `gnuoctave/octave:9.2.0` (index sha256:100d394c..., amd64 manifest sha256:32e37faa..., layers checked against their diff ids: `provenance/octave.unpack.json`). The SIF reproduces part 1's south block byte for byte (m90, mclim, mhw_ts).
- Step_2 sharded: 24 shards of whole columns of Step_1's 449 x 379 layout (449 consecutive sea cells each, latitude-major), `shards/shards.txt`; `detectc` treats cells independently. Rehearsal columns computed in other shards (20 columns) are bit-identical to the same columns here (`logs/shard_invariance.log`).
- Step_3 (the authors' finder, verbatim) ran on the merged 449 x 379 x 15338 array of all 24 shards (`step3/`).
- Reference: `icsa.refdet` computed fields, float64, Hazen, on the same S1 values and cells, in 192 chunks of 2 columns (`cmp_chunks.jsonl`), counts summed, event days OR-ed. The chunk function equals `tools/octave/criterion.block` on all six part-1 blocks (`logs/selftest.log`).
- Time: Step_2 15:52-16:02Z on jobs job_2 and 25695800 (3.73 core-hours of detectc, summed over the 24 shards' logs), Step_3 1 min, comparison 5 min.

## Result (`domain.json`)

| part | result |
|---|---|
| 1 thresholds | m90 max abs diff 3.0517578125e-05 K (exactly 1 float32 ulp at 256-512 K, the bound), mclim 8.4e-06 K; 60,768,078 cell-days of year compared each; 0 above the bound; no NaN mismatch |
| 2 event state | Octave 285,688,750 event cell-days, reference 285,685,463; raw differing 9,949 (3.5e-5); 11,595 exceedance flips, all at the boundary (max 0.532 ulp from the reference threshold), 0 off the boundary; 5,890 of the differing cell-days are themselves boundary cell-days; **residual after the boundary patch 0** |
| 3 events | identical before any patch: 154 events, 12,288 active days, same onset and end (ours only 0, Octave only 0); Step_3 as run equals the list from the cell-day states |
| 4 positive control (single-precision emulation) | fields bit-identical on 192/192 chunks (NaN payloads too), 0 differing cell-days, events identical |

Criterion passes on all four parts.

## Against the published 189 (same for Octave's list and the reference's, as the two are identical)

154 events; 21/189 exact onset and end; 179 published events overlapped (18 by several of ours); 15 of ours overlap none. This equals part 1's Step B mode (b) on BALarea (154, 21, 179, 18, 15; 12,288 active days), fixed in PREREG before the run. Offset histograms and the lists of events only in one catalogue are in `domain.json`.

## Limits

- Octave, not MATLAB: Octave compares single SST with the double threshold in single precision (`SCOPE.md` §1); no MATLAB run exists.
- The m90 maximum equals the 1-ulp bound (3.0517578125e-05 K); it passes `<= 1 ulp`. Part 1 also reached exactly 1 ulp, in its nanpaths block (README §3). Here 4 of 192 chunks reach it and 106 exceed part 1's 2.13e-5. The cell holding the maximum (packed cell 143,972, day-of-year index 66, `logs/locate_max.log`) has no NaN day in its baseline, so this is the single-precision rounding of Octave's quantile and not a NaN-path effect.
- A 20-column rehearsal (timing, a partial Step_3) preceded the run; it is not part of any number here and is kept apart (`rehearsal/` in the run directory).
- Run directory on site-a: `$SCRATCH/icsa-octave-domain` (700), with `manifest_all.txt` (sha256 and size of every file).
