# Time axis, initialisation or product version? (science question on #4, 1 Nov)

> Scope (`SCOPE.md` §2): the data-version attribution is "consistent with", not "caused by"; the reconstruction is tested by the round trip in `diag/roundtrip.md`.

Data: `diag/timeaxis.md`, from `tools/diag/diag_timeaxis.py`. It uses no thresholds: the rebuilt authors' SST (event map + published mclim) is compared directly with our raw 202506 SST, read as MATLAB ncread does. All event files used are checked against the publisher's md5 and size.

Documents (read 1 Nov 2026):
- PUM: [CMEMS-SST-PUM-010-016](https://host-23.invalid/PUM/CMEMS-SST-PUM-010-016.pdf), Issue 4.0, June 2025;
- QUID: [CMEMS-BAL-QUID-010-016-040](https://host-23.invalid/QUID/CMEMS-SST-QUID-010-016-040.pdf), Issue 4.0, 14 Feb 2025;
- the release notice: [Copernicus Marine release of 25 June 2025](https://marine.copernicus.eu/user-corner/user-notification-service/cmems-new-service-release-25th-june-2025).

## 1. Time axis: no global label offset

- **The published time coordinates are labels the authors' code builds.** It never reads them from their SST files:
  - Step_2 sets `time=datenum(1982,1,1):datenum(2023,12,31)` and takes the k-th SST field as that day;
  - Step_4 sets `mhw_time=datetime(1982,1,2,12,0,0):days(1):…`. The event files hold 1982-01-02T12:00 etc. (seconds since 1970).
  - BALMHW_supp.nc holds day of year 1..366.
  - Our raw files hold 00:00 UTC stamps (seconds since 1981-01-01, proleptic Gregorian). The PUM §2d (p. 11) gives "Reference Time 00 UTC, Product temporal coverage 0 to 24" hours; the QUID §II (p. 10) gives the aggregation as "the analysis +- 12 hours".
  - So an offset in the authors' data cannot show in any published time coordinate. It can show only in the values.
- **Shift −1 against shift 0, every verified event (15 of 189 on disk, 1982–1989), all days, all MHW cell-days** (table in `timeaxis.md`):
  - Shift −1 wins only for event 001 (1982-01-02..08): exact 0.428 against 0.007, mean abs d 0.009 against 0.083 K.
  - For every later event shift −1 is worse, e.g. 002: 0.301 against 0.098 K; 005: 1.106 against 0.534 K; 006: 0.436 against 0.232 K.
  - Pooled over 157,847 cell-days: shift 0 gives 1.35 % exact and mean abs d 0.333 K; shift −1 gives 1.19 % and 0.641 K.
  - A global offset would give near-100 % at −1 everywhere. It does not.
  - The verified events end in 1989. The later ones are still downloading, and the table will be extended when they arrive.

## 2. Decay at the start (rebuilt cells only)

The authors' SST is published only on MHW cell-days, so "all cells finite in both" cannot be used. These are the cells of event 001, the only published cells in 1982-01-02..14.

| authors' day | rebuilt cells | exact vs our previous day | exact vs our same day |
|---|---|---|---|
| 1982-01-02 | 205 | 1.000 | 0.000 |
| 1982-01-03 | 232 | 0.582 | 0.000 |
| 1982-01-04 | 232 | 0.422 | 0.000 |
| 1982-01-05 | 232 | 0.233 | 0.009 |
| 1982-01-06 | 232 | 0.138 | 0.022 |
| 1982-01-07 | 184 | 0.234 | 0.011 |
| 1982-01-08 | 7 | 0.000 | 0.000 |
| 1982-01-09..14 | 0 (no published MHW cell) | n/a | n/a |

## 3. Initialisation and version, from the documentation

- **Persistence: yes.**
  - QUID §II (p. 10): "The SST reprocessing subsystem running at DMI uses a persistence approach based on the use of the previous analysis field as a first guess … The SST observations from the current day are therefore interpreted as anomalies with respect to the first guess field."
  - PUM §2f (p. 11): "Each daily SST analysis is based on aggregated input data from the analysis day. The previous days analysis is used as a first guess field for the OI processing system." The same is in PUM §2b (p. 8).
  - Two runs that share a starting field therefore agree exactly wherever no observation has entered yet, and drift apart as each run's own observations accumulate. That is the decay of section 2: January, cloudy, few observations.
- **The first analysis: not documented.** PUM p. 9 lists "Initial conditions: N/A". Neither document says how 1 January 1982 is initialised, nor whether two versions share a start field. The one-day offset at the start (their second field equals our first) has no documented cause.
- **The version change: documented, and large.**
  - QUID §V (p. 32), change log:
    - "10/09/2020 Upstream data change from ESA SST_cci (v2.1) L2P to C3S ICDR L3U";
    - "10/06/2025 Full reprocessing with new version of ESA SST_cci v3.0 / Change in under-ice temperature value from constant to salinity-based update / New, higher resolution land mask".
  - QUID §VI.2 (p. 33): "Up to 2023, the product used ESA SST_cci V2.1 input data (L2P from 1982-Aug 2019 and L3U from September 2019 to December 2023). In 2024, the product was fully reprocessed using updated L2P input data from the ESA CCI SST v3.0 dataset for the period 1982 to 2021."
  - PUM record table, Issue 4.0 (2025-06-15): "Full Reprocessing using ESA CCI SST v3.0 for the period 1982-2021, ICDR SST for 2022-2024".
  - The release notice of 25 June 2025: "Full reprocessing of the Baltic Sea Multi-Year L3S and L4 SST products based on the ESA_CCI SST v.3.0 dataset". The authors downloaded on 25 April 2025, before this release.

## Answer

- **Both effects are present, and they are separable.** The start-of-record match is an initialisation effect, not a time-axis error:
  - it holds only in the first week of 1982 and decays as persistence carries each run's own observations forward;
  - no constant label shift fits any later event.
- **Everything after that week is the product-version change the documents record.** The changes are:
  - the inputs, ESA SST_cci v2.1 → v3.0 for the whole of 1982–2021;
  - the under-ice temperature, which changed from a constant to a salinity-based value;
  - a new, higher-resolution land mask.
- **The two later changes match the Step A diagnosis (`diagnosis.md`):**
  - the largest differences fall in the ice season of the northern Baltic (63.9° N: 0.81 K in April, 0.52 K in January);
  - 7,019 cells have SST in 202506 but none in the authors' data.
- The one-day offset in the first field remains unexplained by the documentation. It affects only event 001 (1982-01-02..08).

## Closed (science agent, #4, 1 Nov)

- **What explains the start of the record:** persistence (a shared first field, carried forward by the previous-day first guess) plus the documented reprocessing.
- **The one-day offset of the shared first field:** a curiosity, not an issue for the study. It affects only event 001 (January 1982), and the study's required extent starts at 1991-12-27.
- No further work on the time axis.
