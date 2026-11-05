# Whole-domain Octave run: what is fixed before any production output (#34 item 9)

Written 5 Nov 2026, before the production run. The shards and numbers seen so far come from a 20-column rehearsal for timing
(`rehearsal/` on site-a): they are not results and are recomputed from scratch in fresh directories.

## The run

- Input: the BALarea cells (170,171, `data._full_sea_mask()`) of the 202506 S1 record, 1982-01-01..2023-12-31 (15,340 days), packed from
  the site-a master copy `dataset.tar` (every file checked against its manifest sha256), in the authors' Step_1 order, reshaped 449 x 379.
- Code: the authors' Step_2 call as written, `detectc` of m_mhw commit a7bdda7 with the existing patch and shims, unchanged (patched
  `detectc.m` sha256 3c35ac02..., as in part 1's PROVENANCE). Detection 1982-01-02..2023-12-30, baseline 1992-2002.
- Step_2 is sharded by whole columns of the 449 x 379 array (449 consecutive sea cells each, latitude-major). Cells are independent in
  `detectc`. Step_3 (the authors' finder, verbatim) reads all 379 columns merged into one 449 x 379 x 15338 array.
- GNU Octave 9.2.0, image `gnuoctave/octave:9.2.0` (index sha256:100d394c..., amd64 manifest sha256:32e37faa...), run as an Apptainer SIF
  built from that archive's layers (each layer's sha256 checked against its diff id), BLAS threads 1.

## The criterion (unchanged: protocol/parameters.md, "Equivalence criterion", and tools/octave/criterion.py)

Reference = `icsa.refdet` computed fields in float64, Hazen, on the same S1 values and the same cells; domain event rule.
1. `m90`/`mclim` max |Delta| <= 1 float32 ulp at the field's magnitude (3.05e-5 K), over all cells.
2. Cell-day event states: raw differing count; those at the boundary (within 1 ulp of the reference threshold); the residual after setting the
   boundary exceedances to the authors' values and re-applying the run rules. Passes if the residual is 0 and no flip lies off the boundary.
3. The two domain event lists compared (identical, or identical after the boundary patch, each case listed).
4. Positive control: precision="octave" emulation gives bit-identical fields, cell-day states and events (feasible at this size).
Nothing is tuned. A failure is reported as it is, with the residual listed.

## Expected before looking (part 1, `stepB_authors_domain/events_by_domain.json`, mode (b), BALarea)

The chunked float64 reference on the same S1 and cells must reproduce part 1's Step B result, which came from another code path
(`validate.py`, band-wise): 154 events, 21/189 exact onset and end, 179 published events overlapped (18 by several), 15 of ours
overlapping none, 12,288 active days. A mismatch would be a pipeline bug, not a criterion result.

## Checks that tie the chain together (done before the run)

- Packed cells equal part 1's block inputs bit for bit on south, oslo, bothnian, archip, y1982 and the full-record round-trip block
  (`verify_pack.py`; the blocks' sha256 are in part 1's README).
- The SIF reproduces part 1's south block: m90, mclim and mhw_ts byte-identical (sha256).
- `domain_criterion.py selftest` equals `criterion.block` on all six part-1 blocks.
