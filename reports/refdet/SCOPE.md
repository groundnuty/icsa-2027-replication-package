# What the #4 validation shows, and what it does not

This scope applies to every report under `reports/refdet/`. The frozen reports keep their original text; the scope given here governs how they are read.

## 1. Implementation equivalence: under GNU Octave 9.2.0, in six blocks

- **The claim.** Our reference detector is equivalent to the authors' code (m_mhw `detectc.m`, as their Step_2 calls it) **as executed by GNU Octave 9.2.0** (docker `gnuoctave/octave:9.2.0`, image `sha256:100d394c…`), **on the six blocks** south, oslo, bothnian, archip, nanpaths and y1982, under the fixed four-part criterion of protocol/parameters.md.
- **It is not a claim about native MATLAB.**
  - Octave compares the single SST with the double threshold in single precision: it rounds `m90` to single before `>=` (`tools/octave/t_semantics.m`: `single(0.1) == 0.1` is true in Octave).
  - MATLAB's documented comparison of mixed single and double does not lose that precision.
  - So MATLAB and Octave can disagree on boundary cell-days whose SST lies within one float32 ulp of the threshold.
  - No MATLAB run was made (no licence), and the size of that difference is not measured.
- **The reference.** It computes in float64 throughout (science decision on #4). Against Octave it differs only on such boundary cell-days (criterion 2), within 0.36 float32 ulp of its own threshold in every block (`octave_equivalence_r3.md`).

## 2. The data-version attribution: consistent with, not yet caused by

- **What the evidence shows.** The rebuilt authors' SST differs from 202506 on the published MHW cell-days. The pattern (season, ice, water mask) matches the changes the Copernicus documentation records for the June 2025 reprocessing: ESA SST_cci v2.1 → v3.0, under-ice temperature, land mask (`diag/timeaxis_answers.md`).
- **How it is worded.** The Step A and Step B gaps are *consistent with* that product-version change. They are not shown to be *caused* by it, because the authors' input files are not available to us.
- **The reconstruction itself.** It is tested by a round trip of the authors' own Step_2 → Step_3/Step_4 export under Octave on 202506 (`diag/roundtrip.md`).

## 3. The production ground truth uses a different sea-cell rule from Step B

- **Production.** The ground truth uses the prompt's sea-cell rule: a cell is sea iff its SST is finite on every day of 1991-12-27..2003-01-05 and of the target period. This is a study adaptation, so that agent and reference agree on sea cells by construction.
- **Step B and the equivalence.** These use the authors' domain (the bathymetry mask = BALarea, or the published-m90-finite cells). Step B's catalogue figures describe the data-version effect. They are **not** attached to the production ground truth.
- **The per-box differences** between the two rules are in `diag/box_domains.md`.
  - Over the 50 instances: finite rule 167,492 cells; ∩ BALarea 153,030; ∩ the authors' domain 150,168; finite outside BALarea 14,462; BALarea cells the rule drops 1,326.
  - **Two of #5's 25 boxes, R22 (63.83–65.03° N, 9.05–10.25° E) and R24 (64.69–65.89° N, 10.25–11.45° E), lie off the Norwegian coast, entirely outside BALarea.** All their finite cells (3,346 and 3,348) are outside the authors' Baltic domain.
  - In the other 23 boxes, 2–65 finite cells per box lie outside BALarea, mostly along coasts and in the Kattegat/Skagerrak.

## 4. How Step B is quoted

"21/189 exact onset and end; 179/189 published events temporally overlapped".
- The overlap figure is near its chance level: random placement of the 189 published durations gives 172.8 [165, 180] overlapped (`diag/overlap_null.md`). Quote it only with that null.
- The exact matches are far above chance: the null is 0.0 [0, 1]. Computed mode on 202506, BALarea domain (`stepB_s1read/validation.md`). No report states a percentage "reproduction" of the catalogue.
