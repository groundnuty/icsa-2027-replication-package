# Step A diagnosis (issue #4): why computed fields on 202506 differ from the published fields

> Scope (`SCOPE.md` §2): the data-version attribution is "consistent with", not "caused by"; the reconstruction is tested by the round trip in `diag/roundtrip.md`.

Written 2026-11-01 by the #4 lane. The scripts are in `tools/diag/` and run from the worktree with `uv run python tools/diag/<script>`.
The only ground truth used is the published material: `BALMHW_supp.nc` and `BALMHW_event_NNN.nc`. Nothing our detector produces is used as an expectation.

## Step A numbers (from `fields_matlab_read/validation.md`, run 2026-10-31T21:27Z, raw read as MATLAB ncread does: fill value only)

| field | mean abs Δ | max abs Δ | cell-days with abs Δ > 0.01 K | > 0.1 K | > 1 K |
|---|---|---|---|---|---|
| m90 | 0.148 K | 3.52 K | 94.6 % | 51.2 % | 0.74 % |
| mclim | 0.116 K | 2.55 K | 93.1 % | 42.2 % | 0.43 % |

Shares are of 58,199,124 cell-days and come from the stored histogram (edges 1e-2, 1e-1, 1). A per-cell share is still to come, from the S1 rerun.

## 1. Data identity: rebuilding the authors' SST (`tools/diag/diag_recon.py 3`)

In detectc, `mhw_ts = temp - mclim` on MHW cell-days, and Step_4 writes it as `MHW_int_maps`. Step_5 writes the same `mclim`. So map + published mclim gives the SST the authors analysed on those cell-days, to float32 rounding (about 1e-5 K).
The script compares that with our raw 202506 SST for the first 3 days of every readable event file.

Literal output (48 of the 61 event files present are unreadable, partial downloads):

```
BALMHW_event_001.nc: days 7 cell-days 669 |d|<1e-3: 0.0000  mean d +0.0832  mean|d| 0.0835  p99|d| 0.1300  max|d| 0.130  MHW cell but raw NaN 0
BALMHW_event_002.nc: days 8 cell-days 497 |d|<1e-3: 0.0845  mean d +0.0437  mean|d| 0.0652  p99|d| 0.4004  max|d| 0.460  MHW cell but raw NaN 0
BALMHW_event_003.nc: days 11 cell-days 848 |d|<1e-3: 0.0236  mean d +0.2243  mean|d| 0.3468  p99|d| 1.8653  max|d| 2.590  MHW cell but raw NaN 0
BALMHW_event_004.nc: days 5 cell-days 3 |d|<1e-3: 0.0000  mean d -0.1567  mean|d| 0.1567  p99|d| 0.2196  max|d| 0.220  MHW cell but raw NaN 0
BALMHW_event_009.nc: days 6 cell-days 375 |d|<1e-3: 0.0000  mean d -0.2461  mean|d| 0.2461  p99|d| 0.3000  max|d| 0.310  MHW cell but raw NaN 0
BALMHW_event_010.nc: days 5 cell-days 30 |d|<1e-3: 0.0000  mean d -0.0260  mean|d| 0.0260  p99|d| 0.0400  max|d| 0.040  MHW cell but raw NaN 0
BALMHW_event_017.nc: days 8 cell-days 1088 |d|<1e-3: 0.0037  mean d +0.6885  mean|d| 0.8079  p99|d| 2.1213  max|d| 2.470  MHW cell but raw NaN 0
BALMHW_event_018.nc: days 8 cell-days 608 |d|<1e-3: 0.0000  mean d +0.8982  mean|d| 0.8982  p99|d| 1.4193  max|d| 1.550  MHW cell but raw NaN 3
BALMHW_event_020.nc: days 10 cell-days 271 |d|<1e-3: 0.0000  mean d +1.5763  mean|d| 1.5852  p99|d| 2.5630  max|d| 2.850  MHW cell but raw NaN 7
BALMHW_event_021.nc: days 5 cell-days 9 |d|<1e-3: 0.0000  mean d +0.4078  mean|d| 0.4078  p99|d| 1.6236  max|d| 1.710  MHW cell but raw NaN 0
BALMHW_event_024.nc: days 11 cell-days 959 |d|<1e-3: 0.0094  mean d +0.0841  mean|d| 0.0855  p99|d| 0.1000  max|d| 0.100  MHW cell but raw NaN 25
BALMHW_event_029.nc: days 5 cell-days 3 |d|<1e-3: 0.0000  mean d +0.1400  mean|d| 0.1400  p99|d| 0.1600  max|d| 0.160  MHW cell but raw NaN 0
BALMHW_event_034.nc: days 5 cell-days 48 |d|<1e-3: 0.0000  mean d -0.0848  mean|d| 0.0956  p99|d| 0.1553  max|d| 0.160  MHW cell but raw NaN 0
ALL: cell-days 5408, share |d|<1e-3 0.0139, share |d|<0.01 0.0259, mean d +0.3656, mean|d| 0.4477, max|d| 2.850
```

Identical data would give abs d of about 1e-5 on every cell-day. Only 1.4 % of cell-days agree to 1e-3, about what chance agreement on the 0.01 K quantisation predicts.
The positive mean d is expected: the cells were selected because the authors' SST was high.

## 2. The rebuild is self-consistent (`tools/diag/diag_mask_consist.py`, part a)

```
(a) on published MHW cell-days, share rec SST >= published m90: 19465/19465 = 1.0000
(a) on published MHW cell-days, share raw SST >= published m90: 13546/19465 = 0.6959
```

Events 001, 002, 003, 009, 017, 018, 020, 024 and 034, all days. The rebuilt SST passes the published threshold on every published MHW cell-day; our 202506 SST passes on only 70 %.

## 3. No indexing artefact (`tools/diag/diag_shift.py`)

Day shifts of −3..+3 and one-cell lat/lon shifts were tested on events 001, 003, 017 and 024, first 3 days. No alignment brings abs d near 0: the best mean abs d per event is 0.067–0.79 K, and the share below 1e-3 stays ≤ 2 %. For example, event 003 has unshifted mean abs d 0.347 and best (lat −1, lon +1) 0.327; a −1 day shift gives 1.91.
The supp.nc and raw latitude and longitude vectors are equal (max diff 0.0).

## 4. Sea mask (`tools/diag/diag_mask_consist.py`, part b)

```
(b) BALarea finite 170171, ours (nearest bathy) 170171, both 170171, only BALarea 0, only ours 0
    published m90 finite on any doy 159261, on all doys 159261; m90-finite outside BALarea 0; BALarea cells with m90 NaN on all doys 10910
    our raw finite (sampled baseline days) any 185239 all 185239
    BALarea & raw-any & ~m90any (authors' SST NaN where ours finite): 7019
    m90any & ~rawall (published finite where our raw is sometimes NaN): 247
```

- Our sea mask, the BAL-MFC_003_011 bathymetry interpolated with `interpn(..., 'nearest')` as in Step_1, equals finite `BALarea` exactly.
- Inside that mask, 7,019 cells have SST in 202506 but are NaN in every published field. The authors' product had no SST there, so its water mask was different: a second sign of another product version. The 202506 files name "ESA SST CCI v3.0" as their source and were created 2025-01-17.
- 247 cells are finite in the published fields but NaN on some of our sampled baseline days. These are the cells where `quantile` NaN handling and movmean omitnan matter.

## 5. Day alignment per event day (`tools/diag/diag_dayshift.py`, log `diag/diag_dayshift.log`)

For every readable event day the script finds the day shift (−7..+7) of our raw SST that best matches the rebuilt SST:

```
001 1982-01-02 cells    205  shift0: exact 0.000 mean|d| 0.085  best shift -1: exact 1.000 mean|d| 0.000
001 1982-01-03 cells    232  shift0: exact 0.000 mean|d| 0.082  best shift -1: exact 0.582 mean|d| 0.006
001 1982-01-04 cells    232  shift0: exact 0.000 mean|d| 0.084  best shift -1: exact 0.422 mean|d| 0.007
001 1982-01-05 cells    232  shift0: exact 0.009 mean|d| 0.084  best shift -1: exact 0.233 mean|d| 0.010
001 1982-01-06 cells    232  shift0: exact 0.022 mean|d| 0.079  best shift -1: exact 0.138 mean|d| 0.014
001 1982-01-07 cells    184  shift0: exact 0.011 mean|d| 0.077  best shift -1: exact 0.234 mean|d| 0.016
```

- The first published day, labelled 1982-01-02 by the authors, equals our 1982-01-01 on all 205 cells within half a float32 ulp at 280 K (max 1.48e-5 K), which is the rounding of the published single mclim. This is the precision the reconstruction can reach.
  - The table's "exact" means abs d < 1e-3 K. It was earlier mis-described as bit for bit.
  - A uint32 test on the anomalies matches only 3 of 205 (`diag/bits.md`).
  - That is consistent with MATLAB having subtracted the unpublished double climatology (only single(mclim) is published), which would make the uint32 test fail even for identical data.
  - This is an inference, consistent with the half-ulp SST agreement and with the exact round trip under Octave (`diag/roundtrip.md`). It is not shown directly.
- The match then decays over the first week, as two analyses that start from the same state and then diverge would.
- From the second event (March 1982) on, no shift gives more than a few per cent exact matches. The full log has every day.
- So the two versions share their first analysis, and at the start of the record the authors' day labels are one day later than ours. We cannot tell from the outputs whether the old product had an extra leading day or the time stamps changed.
- The offset does not persist into the baseline (section 6, shift test). It only touches the first days of 1982 (event 001).

## 6. Structure of the Step A difference (`tools/diag/diag_fields_band.py 100:116 300:316 520:536`, log `diag/diag_fields_band.log`)

These are three bands of 16 latitude rows: 55.5° N (southern Baltic), 59.5° N, and 63.9° N (Bothnian Bay, seasonal ice).

- **Seasonal.** For m90, mean abs Δ by month in the 55.5° N band runs from 0.188 (Dec) to 0.042 (Sep). At 63.9° N it runs from 0.809 (Apr, ice melt; the day-of-year maximum, 0.93, is on day 104) and 0.524 (Jan) down to 0.044 (Sep). mclim behaves alike. Every cell has some day of year with abs Δ > 0.01 K.
- **No year-end or day-60 artefact.** Doys 1–5 and 362–366 follow their months: winter is the high season. In the north band, doys 1–5 are 0.554 against a January mean of 0.524. Doys 59–61 sit between the February and March means. There is no isolated spike at the pooling boundaries.
- **No persistent label shift in the baseline.** For both fields in all bands, published[i] against ours[i + s] is best at s = 0. For example, for 55.5° N mclim the mean abs Δ is 0.1116 / **0.0819** / 0.1207 for s = −1 / 0 / +1.
- **Not coastal.** For m90, mean abs Δ in open water (no land within 3 cells) is 0.116, 0.140 and 0.240 in the three bands; near land it is 0.078, 0.151 and 0.287.
- **Sign.** Our 202506 values are on average warmer than the published ones, by 0.03–0.10 K for m90 and 0.03–0.08 K for mclim.

A changed product (reprocessed inputs, sea-ice handling) produces this pattern. An error in pooling, smoothing or the estimator would concentrate at the pooling boundaries or show in every season alike.

## 7. The product-version change, as Copernicus documents it

- **Change log.** Copernicus Marine Quality Information Document CMEMS-BAL-QUID-010-016-040, Issue 4.0, 14 February 2025, §V "System's noticeable events, outages or changes", p. 32:
  > 10/06/2025 — Full reprocessing with new version of ESA SST_cci v3.0. Change in under-ice temperature value from constant to salinity-based update. New, higher resolution land mask.
- **Inputs before and after.** Same document, §VI.2 "Reprocessing with ESA SST_cci v3.0", p. 33:
  > Up to 2023, the product used ESA SST_cci V2.1 input data (L2P from 1982-Aug 2019 and L3U from September 2019 to December 2023). In 2024, the product was fully reprocessed using updated L2P input data from the ESA CCI SST v3.0 dataset for the period 1982 to 2021.
- **Timing.** The reprocessing was released on 25 June 2025 (Copernicus Marine release notice). The authors downloaded on 25 April 2025.
- **How the changes match our findings:**
  - the under-ice change and the new land mask match the ice-season pattern of §6;
  - the new land mask also matches the 7,019 extra finite cells of §4.
- Both are read as *consistent with* the version change (`SCOPE.md` §2).

## Conclusion

- The Δ of Step A is a data-version effect. The SST values differ cell by cell, by tenths of a kelvin on MHW days. The difference is seasonal, largest in the ice season. The water mask changed. The two versions share only their first analysis day, with a one-day label offset at the very start of 1982.
- It is not the pooling, the estimator, the mask or the reading, which are what our implementation controls; the Octave equivalence tests those directly.
- Under the 19:44Z decision rule, A does not match, so ground truth is computed mode on 202506 and validation is by implementation equivalence under Octave.
- The published m90 cannot identify the percentile estimator, because the data differ: `linear` scoring closest to it reflects the drift, not evidence about the estimator. The estimator is fixed from the code and checked against Octave.
