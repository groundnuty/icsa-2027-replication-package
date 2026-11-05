# Octave equivalence against the fixed criterion (issue #4)

The authors' detectc.m runs under GNU Octave 9.2.0 on byte-identical input; the input sha256 is in source.json.
The criterion is in protocol/parameters.md, and this script's docstring states it.
The ulp is float32's, at the field's magnitude: 3.05e-5 K.

| block | box | detection | sea / intermittent-NaN cells | 1: m90, mclim max abs diff | 2: differing cell-days (share) / of them boundary / flips at, not at boundary / left after patch | 3: events (Octave) identical / after patch | 4: octave mode bit-identical | pass 1 2 3 4 |
|---|---|---|---|---|---|---|---|---|
| south | 100:130, 100:130 | 2014-01-01..2018-12-31 | 504 / 0 | 1.98e-05, 6.39e-06 | 3 (1.5e-05) / 2 / 3, 0 / 0 | 25: True / True | True | Y Y Y Y |
| oslo | 300:330, 60:90 | 2014-01-01..2018-12-31 | 61 / 0 | 1.95e-05, 5.71e-06 | 0 (0.0e+00) / 0 / 0, 0 / 0 | 12: True / True | True | Y Y Y Y |
| bothnian | 570:600, 630:660 | 2009-01-01..2013-12-31 | 705 / 0 | 2.13e-05, 6.59e-06 | 2 (1.0e-05) / 2 / 9, 0 / 0 | 24: True / True | True | Y Y Y Y |
| archip | 330:360, 600:630 | 2014-01-01..2018-12-31 | 575 / 0 | 2.05e-05, 7.32e-06 | 0 (0.0e+00) / 0 / 4, 0 / 0 | 23: True / True | True | Y Y Y Y |
| nanpaths | 100:130, 100:130 | 2014-01-01..2018-12-31 | 504 / 114 | 3.05e-05, 1.39e-05 | 3 (1.6e-05) / 2 / 3, 0 / 0 | 25: True / True | True | Y Y Y Y |
| y1982 | 30:60, 30:60 | 1982-01-02..1986-12-31 | 118 / 6 | 1.87e-05, 6.31e-06 | 0 (0.0e+00) / 0 / 0, 0 / 0 | 8: True / True | True | Y Y Y Y |

Notes:
- nanpaths, m90 max abs diff: exactly 1 ulp (3.0517578125e-05 K), at the bound. It lies in the NaN-injected rows that leave few finite values per smoothing window: rows 13–14 (40 baseline days per cell) and rows 5–7 (Feb–Mar removed). There a single-precision rounding in Octave's quantile is not averaged down by the 31-day mean. Elsewhere the maximum is ≤ 2.1e-5 K.
- Blocks with cells that are NaN in the published fields but finite in 202506 (inside BALarea): archip 163, bothnian 51, south and nanpaths 46, oslo 27, y1982 20.
- Coastal blocks: oslo (Oslofjord) and archip (Archipelago Sea). Gulf of Bothnia: bothnian, with the ice winters 2009–2013. Intermittent NaN: nanpaths (injected, 114 cells) and y1982 (the 6 out-of-range cells of January 1982 that S1 masks).
- Shim check: after the Codex review, movmean_omitnan.m sums each window directly instead of by prefix sums. South and nanpaths re-run under the new shim give byte-identical m90, mclim and mhw_ts. The other blocks ran with the earlier shim; it gives the same bytes on these inputs, because every sum of the single-valued fields is exact in double.
- The precision used for the reference is float64 (science, #4). precision="octave" exists only for criterion 4.
