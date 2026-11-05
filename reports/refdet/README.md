# Reference detector validation package (issue #4)

**Read `SCOPE.md` first.** It covers four points:
- the equivalence holds under GNU Octave 9.2.0, in six blocks, not native MATLAB;
- the data-version attribution is "consistent with", not "caused by";
- the production sea-cell rule differs from Step B's;
- how Step B is quoted.

The production ground truth uses the prompt's finite-cell rule. This is a study adaptation, and Step B's catalogue figures are not attached to the production ground truth.

This file indexes the evidence the science agent cross-reviews.
- Commits are on `feat/4-refdet`. Scripts run from the repository root with `uv run python …`.
- Data live under `ICSA_DATA` (default `/mnt/volume2/icsa-2027`).
- Files marked **frozen** are kept exactly as committed, at the science agent's request. Later results go in new files.

## Inputs

| input | where | sha256 (or check) |
|---|---|---|
| SST 202506, yearly download (42 files) | `raw/SST_BAL_YYYY.nc` | manifest `raw_sha256.txt`, sha256 `adad859adb34f0df68251c7427057b4a0f694fdee9519b28378c2968e179db95`; `sha256sum -c` re-run on 1 Nov 03:30Z: 42/42 OK |
| SST as the agents read it (S1, 15,340 daily files) | `s1/sst_YYYYMMDD.nc` | built by #3; `verify_s1.log` reports 0 mismatches over 15,340 days. Equal bit for bit to the netCDF4 valid-range read of the raw files (checked again on 4 days, `diagnosis.md`). Each Octave block records the sha256 of the exact S1 bytes it used (below) |
| published fields | `ref/bashiri/data/BALMHW_supp.nc` | `29000d4cd30f23c5b366e4a7e2360fce1fe3020553a13d09a801dc8378482940` (md5 matches the publisher's, `verify.tsv`) |
| published catalogue, 189 events | `ref/bashiri/data/BALMHW_data_info.csv` | `5e1773299058f3b002f1d7057b679a7a2d5855acba69978cf9d72256db4bdf31` |
| published daily event maps | `ref/bashiri/data/BALMHW_event_NNN.nc` | md5 and size against the publisher's list (`todo_events.tsv`). Each run states which files were verified |
| authors' code | `ref/bashiri/code_unzipped/…/Step_2_MHW_detector.m` | `2c7b98294941a6c2a3eb1bdb490f7fae6717469861e648f9fed7ce2cc19f3bb4` |
| m_mhw `detectc.m` (commit a7bdda7) | `ref/m_mhw/detectc.m` | `c1e724053340aecc65b383e8e716eb93e5de5ddd9aa717e52955622035578d9f` |
| bathymetry mask (Step_1), = finite BALarea | `ref/bashiri/code_unzipped/…/mask_bathy/BAL-MFC_003_011_mask_bathy.nc` | `a832db482a3776b7888bb5fd036abe662b687207f550bced4a54469da51b1317` |
| GNU Octave 9.2.0 | docker `gnuoctave/octave:9.2.0` | image `sha256:100d394c57b86469748d26ddafcf73a1074338a66dabcababe2e4e05146772b9` |

## 0. Scope, time axis and domain checks (science review, 1 Nov)

| piece | report | script | commit |
|---|---|---|---|
| scope of the claims | `SCOPE.md` | — | 8869080 (box finding added in 6a7b438) |
| time axis vs initialisation vs version (closed) | `diag/timeaxis_answers.md`, `diag/timeaxis.md` | `tools/diag/diag_timeaxis.py` | f8a8d9f |
| uint32 bit comparison of the anomalies; first-day precision | `diag/bits.md` | `tools/diag/diag_bits.py` | d5dedff |
| round trip of the reconstruction through the authors' Step_2 -> Step_3 -> Step_4 under Octave | `diag/roundtrip.md`, `diag/roundtrip_source.json`; input S1 block sha256 `4c6be30cfc5e37b1b84e686b09f8749811ba0cfe72dd8730eab630930b63e3e9` | `tools/octave/run_export.m`, `tools/diag/roundtrip.py` | 318713d, 620b172 |
| production sea-cell rule against BALarea and the authors' domain, per #5 box | `diag/box_domains.md`, `diag/box_domains_outside_balarea.csv` (boxes: `diag/instances_boxes_5.json` and instances.json of #5 at a5bf6bf); baseline finiteness from the S1 field cache below | `tools/diag/box_domains.py` | 6a7b438 |
| null distribution for the Step B overlap and exact-match counts (1,000 draws, seed 20261101) | `diag/overlap_null.md` | `tools/diag/overlap_null.py` | the commit titled 'docs: Step B overlap null and lakes check in the index' |
| finite cells outside BALarea: lakes, coastal water, open sea; per #5 box | `diag/lakes.md`, `diag/lakes_components.csv` | `tools/diag/lakes.py` | the commit titled 'docs: finite cells outside BALarea classified as lakes, coastal water or open sea' |
| S1 field cache (production ground truth; refused unless its record matches) | `fields_s1.json` (copy of the cache's record), cache on the volume at `refdet/fields_s1/`; S1 fingerprint `712ea74ec9d43ec35a6e42f57060fb7ac5b1425ccf7e095627dc22fbeb939323` | `icsa/refdet/fieldcache.py` (`build`, `check_ground_truth`) | bb78176, 620b172; built 2026-11-01T04:13:48Z |

## 1. Step A: computed fields on 202506 vs the published `m90`/`mclim`

| piece | report | script | commit |
|---|---|---|---|
| fill-only read, as MATLAB `ncread` reads (31 Oct; includes the estimator sweep against the published m90) | `fields_matlab_read/validation.md` | `icsa/refdet/validate.py --stage fields --no-valid-range` (code at 527222c) | 8da23a6 |
| S1-equivalent read (valid range masked), per-cell shares | `stepB_s1read/validation.md`, fields section | `icsa/refdet/validate.py --stage all --no-estimators --band-rows 8 --workers 4 --mask-dir …` (code at 73072c2) | 411ee03 |

Both reads give the same numbers, because every out-of-range value falls in January 1982, outside the baseline.
- m90: max abs Δ 3.52 K, mean 0.148 K.
- mclim: max 2.55 K, mean 0.116 K.
- Every cell (159,014 of 159,014) has some day of year with abs Δ > 0.01 K.

## 2. Data comparison: is 202506 the data the authors analysed?

The rebuilt authors' SST is the event map plus the published mclim, on published MHW cell-days.

| piece | report / log | script | commit |
|---|---|---|---|
| summary and diagnosis | `diagnosis.md` | (the scripts below) | 046ad75, 5b74bfa |
| rebuild on all 13 readable event files, all days (**frozen**) | `diag/diag_recon_alldays.log` | `tools/diag/diag_recon.py` (version of 046ad75, no arguments) | 046ad75 |
| rebuild on the 4 files verified first (004, 009, 010, 021), all days (**frozen**) | `diag/diag_recon_verified4.log` | `tools/diag/diag_recon.py 1000000 4 9 10 21` (version of 9dd9fda, **frozen**) | 9dd9fda |
| day and cell alignment | `diag/diag_shift.log`, `diag/diag_dayshift.log` | `tools/diag/diag_shift.py`, `tools/diag/diag_dayshift.py` | 046ad75, 5b74bfa |
| self-consistency and sea masks | `diagnosis.md` §2, §4 | `tools/diag/diag_mask_consist.py` | 046ad75 |
| structure of the Step A difference (season, coast, ice, day-of-year shift) | `diag/diag_fields_band.log` | `tools/diag/diag_fields_band.py <out> 100:116 300:316 520:536` | 5b74bfa |

All 13 event files used were checked against the publisher's size and md5.

Results:
- **Verified 4:** 949 MHW cell-days. 0 % bit-equal, mean abs d 0.261 K, max 1.71 K. Rebuilt SST ≥ published m90 on 100 %.
- **All 13:** 19,540 cell-days. 1.3 % bit-equal, mean abs d 0.32 K, max 2.85 K.
- **Alignment:** no day or cell shift aligns the two. The first published day (authors' 1982-01-02) equals our 1982-01-01 within half a float32 ulp at 280 K (max 1.48e-5 K, the rounding of the published single mclim; `diag/bits.md`), and the match decays over the following week.
- **Time axis:** this is an initialisation effect, not a label offset (`diag/timeaxis_answers.md`).
- **Sea mask:** our sea mask equals BALarea exactly (170,171 cells).
- **Conclusion:** the input data changed (product version), not the computation.

## 3. Implementation equivalence: the authors' detectc.m under Octave on identical S1 data (primary validation)

| piece | report | script | commit |
|---|---|---|---|
| Octave semantics on hand-computed vectors (15/15) | `diag/octave_semantics.log` | `tools/octave/t_semantics.m` | 046ad75 |
| six blocks against the fixed criterion (**frozen**) | `octave_equivalence.md`, `.json` | `tools/octave/criterion.py` (version of cda41ca) | cda41ca |
| second run, criterion 4 as bit patterns (Codex round 2) | `octave_equivalence_r2.md`, `.json` | `tools/octave/criterion.py` | 1c7edda |
| third run, criterion 2 measured against our threshold only (Gemini Argon per-module review) | `octave_equivalence_r3.md`, `.json` | `tools/octave/criterion.py` | 6498300 |
| per-block record and the estimator sweep against Octave's m90 (all six blocks) | `octave_blocks_estimators.md`, `octave_blocks/<block>/` | `tools/octave/compare_block.py`, `tools/octave/summarize.py` | e13a916; bothnian added by the commit 'docs: bothnian in the estimator table' |

The block tools are in `tools/octave/` (README): `prepare.sh`, the patch, the shims, `run_block.m`, `make_input.py` and `make_nan_block.py`. Code provenance (sha256 of the patched detectc.m and the shims) is in `octave_blocks/PROVENANCE_first_runs` for the first runs of all six blocks, and in `octave_blocks/PROVENANCE` for the re-runs of south and nanpaths under the direct-sum movmean shim. Those re-runs gave byte-identical m90, mclim and mhw_ts.

Block inputs (S1; sha256 of the exact bytes Octave and we both read):

| block | box (lat, lon) | detection | sha256 of input |
|---|---|---|---|
| south | 100:130, 100:130 | 2014–2018 | `574c277a411619f1bcb588247915d451ebb8a8afad58a04bfb076a089d6a380b` |
| oslo (coast) | 300:330, 60:90 | 2014–2018 | `87cfdfccd6b6e4b0679a7e6537552f3ba049d03db20f4df4ef0143e8fa805e0f` |
| bothnian (Gulf of Bothnia, ice) | 570:600, 630:660 | 2009–2013 | `a1662cce104b15c996a137f0734b500ff6e81e1e7a46fcc502f5714386a3e800` |
| archip (coast; 163 cells NaN in the published fields, finite in 202506) | 330:360, 600:630 | 2014–2018 | `6ccaa5f11959aea37ef77dd119e6338061cb2c6d9c1c521dc32bf621e6ae5402` |
| nanpaths (south with documented NaN injection, seed 0) | 100:130, 100:130 | 2014–2018 | `f92b933fb4e7083243e541353da09994ffb87be130fffba35a189a2c751ec991` |
| y1982 (the out-of-range cells S1 masks) | 30:60, 30:60 | 1982-01-02..1986-12-31 | `b1fb891b516d7d9bb97080fe843a4cbd1f85c2742ad35189a8ad9bf7bef09866` |

Results:
- All six blocks pass criteria 1–4.
- Thresholds are within 1 float32 ulp (≤ 2.13e-5 K on unmodified data; exactly 1 ulp in nanpaths).
- Every differing cell-day is explained by exceedances within 1 ulp of the threshold. The raw, at-boundary and residual counts are in the table; the residual is 0 in every block.
- Events are identical, and `precision="octave"` is bit-identical.
- The estimator measured against Octave's m90 is Hazen, at about 8e-6 K mean; the next best is ≥ 6e-3 K.

## 4. Step B: modes (a) and (b) on 202506 against the 189 events (the data-version effect, reported, never tuned)

| piece | report | script | commit |
|---|---|---|---|
| events, overlaps, offsets; daily maps for the files on disk | `stepB_s1read/validation.md`, `.json`, `run.log`, `masks_sha256.txt` | `icsa/refdet/validate.py --stage all …` (code at 73072c2) | 411ee03 |
| events on BALarea and on the authors' effective domain (published m90 finite) | `stepB_authors_domain/events_by_domain.md`, `.json` | `icsa/refdet/validate.py --events-from /mnt/volume2/icsa-2027/refdet/stepB` (per-cell masks of 411ee03, sha256 in `stepB_s1read/masks_sha256.txt`) | 7ae735c |
| daily maps on the checksum-verified event files only: n = 30 of 189 (events 001-024, 026-030, 034; 1982-1989), both modes, both domains. Downloads stopped on 1 Nov 2026 (30 verified, 31 truncated, 128 missing) | `stepB_maps_verified.md`, `.json` | `tools/diag/maps_verified.py` (calls `validate.map_agreement` on the masks of 411ee03) | the commit titled 'docs: daily-map agreement on the 30 checksum-verified event maps' |

Events (overlapped = published events overlapped by one of ours):

| mode | domain | events | exact | overlapped |
|---|---|---|---|---|
| (a) published fields | BALarea, 170,171 cells | 186 | 20/189 | 181 |
| (a) published fields | authors' domain, 159,261 cells | 186 | 20/189 | 181 |
| (b) computed | BALarea, 170,171 cells | 154 | 21/189 | 179 |
| (b) computed | authors' domain, 159,261 cells | 154 | 20/189 | 179 |

- (a) is the same on both domains: the published thresholds are NaN on the extra cells.
- The domain effect, (b) on the two domains, is small: 17 active days in 42 years.
- The threshold effect is (a) against (b) on the authors' domain: the SST is held fixed and only the thresholds change. It gives 186 against 154 events.
- The SST effect is (a) against the published events: the published thresholds are fixed and the SST changes. It gives 186 events against 189, with 20 exact.
- Daily maps, n = 30 of 189 events (checksum-verified files, 1982–1989 only; never quote these catalogue-wide). BALarea:
  - (a): pooled Jaccard 0.396, per-event mean 0.277;
  - (b): pooled 0.358, per-event mean 0.238.
  - The earlier 14-file figures are superseded.
- Against chance (`diag/overlap_null.md`), the overlap count is uninformative: mode (b) on BALarea has 179 observed against a null of 172.8 [165, 180] (P = 0.058).
- The exact onset+end matches are informative: 21 observed against a null of 0.0 [0, 1] (none of 1,000 draws reached it).

## Code under validation

- `icsa/refdet/`: `core.py`, `__init__.py`, `truth.py`, `fieldcache.py`, `data.py`.
- Tests are in `tests/refdet/`, with hand-derived expectations.
- The scoring adapter is `icsa/scoring/reference.py`.
- Cross-reviews (Codex Astra, Gemini Argon) are recorded in the PR.
