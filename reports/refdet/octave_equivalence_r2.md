# Octave equivalence against the fixed criterion (issue #4)

> Scope (`SCOPE.md` §1): equivalence with the authors' code as executed by GNU Octave 9.2.0, on these six blocks; not a claim about native MATLAB.

Second run (r2), after the second Codex review: criterion 4 now compares uint64 bit patterns of every non-NaN value and requires identical NaN positions; NaN payloads are reported in the .json and are identical as well. Criteria 1-3 and every number match the frozen first report (octave_equivalence.md, cda41ca), which is left unchanged.

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
