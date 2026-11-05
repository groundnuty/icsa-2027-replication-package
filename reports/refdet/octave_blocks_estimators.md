# Octave equivalence of the reference detector (issue #4)

> Scope (`SCOPE.md` §1): equivalence with the authors' code as executed by GNU Octave 9.2.0, on these six blocks; not a claim about native MATLAB.

Each row compares one block of the authors' detectc.m, run under GNU Octave 9.2.0 (tools/octave), with ours on byte-identical input.
The input sha256 is in each block's source.json.
Octave's output is the only expectation.

Columns:
- *f64*: our default float64 chain;
- *oct*: `precision="octave"`, which emulates Octave's single-precision quantile, mean and comparison;
- *octF*: Octave's own fields through our detection, which isolates the run rules.

| block | box (lat0:lat1, lon0:lon1) | detection | sea cells | intermittent-NaN cells | m90 max abs diff f64 / oct | mclim f64 / oct | cell-days in events (Octave) | differ f64 / oct / octF | flips (max ulp) | active days differ f64 / oct | events (Octave) | events identical f64 / oct / octF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| south | 100:130, 100:130 | 2014-01-01..2018-12-31 | 504 | 0 | 2.0e-05 / 0.0e+00 | 6.4e-06 / 0.0e+00 | 206426 | 3 / 0 / 0 | 3 (0.23) | 0 / 0 | 25 | True / True / True |
| oslo | 300:330, 60:90 | 2014-01-01..2018-12-31 | 61 | 0 | 1.9e-05 / 0.0e+00 | 5.7e-06 / 0.0e+00 | 7870 | 0 / 0 / 0 | 0 (0.00) | 0 / 0 | 12 | True / True / True |
| bothnian | 570:600, 630:660 | 2009-01-01..2013-12-31 | 705 | 0 | 2.1e-05 / 0.0e+00 | 6.6e-06 / 0.0e+00 | 191467 | 2 / 0 / 0 | 9 (0.35) | 0 / 0 | 24 | True / True / True |
| archip | 330:360, 600:630 | 2014-01-01..2018-12-31 | 575 | 0 | 2.0e-05 / 0.0e+00 | 7.3e-06 / 0.0e+00 | 189739 | 0 / 0 / 0 | 4 (0.29) | 0 / 0 | 23 | True / True / True |
| nanpaths | 100:130, 100:130 | 2014-01-01..2018-12-31 | 504 | 114 | 3.1e-05 / 0.0e+00 | 1.4e-05 / 0.0e+00 | 184007 | 3 / 0 / 0 | 3 (0.23) | 0 / 0 | 25 | True / True / True |
| y1982 | 30:60, 30:60 | 1982-01-02..1986-12-31 | 118 | 6 | 1.9e-05 / 0.0e+00 | 6.3e-06 / 0.0e+00 | 15103 | 0 / 0 / 0 | 0 (0.00) | 0 / 0 | 8 | True / True / True |

## Percentile estimator against Octave's m90 (mean abs diff, K)

| estimator | south | oslo | bothnian | archip | nanpaths | y1982 |
|---|---|---|---|---|---|---|
| hazen | 8.94e-06 | 9.41e-06 | 7.19e-06 | 8.92e-06 | 7.84e-06 | 8.59e-06 |
| normal_unbiased | 6.77e-03 | 7.83e-03 | 8.31e-03 | 8.89e-03 | 6.46e-03 | 5.99e-03 |
| median_unbiased | 9.03e-03 | 1.04e-02 | 1.11e-02 | 1.19e-02 | 8.62e-03 | 7.99e-03 |
| weibull | 2.71e-02 | 3.13e-02 | 3.33e-02 | 3.56e-02 | 2.59e-02 | 2.40e-02 |
| linear | 2.71e-02 | 3.14e-02 | 3.33e-02 | 3.56e-02 | 3.19e-02 | 2.40e-02 |
| inverted_cdf | 2.71e-02 | 3.14e-02 | 3.33e-02 | 3.56e-02 | 2.39e-02 | 2.40e-02 |
| averaged_inverted_cdf | 2.71e-02 | 3.14e-02 | 3.33e-02 | 3.56e-02 | 2.38e-02 | 2.40e-02 |
| closest_observation | 2.71e-02 | 3.14e-02 | 3.33e-02 | 3.56e-02 | 2.71e-02 | 2.40e-02 |
| lower | 2.71e-02 | 3.14e-02 | 3.33e-02 | 3.56e-02 | 7.42e-02 | 2.40e-02 |
| higher | 2.71e-02 | 3.14e-02 | 3.33e-02 | 3.56e-02 | 2.40e-02 | 2.40e-02 |
| midpoint | 2.71e-02 | 3.14e-02 | 3.33e-02 | 3.56e-02 | 4.85e-02 | 2.40e-02 |
| nearest | 2.71e-02 | 3.14e-02 | 3.33e-02 | 3.56e-02 | 2.62e-02 | 2.40e-02 |
| interpolated_inverted_cdf | 3.36e-02 | 3.86e-02 | 4.09e-02 | 4.41e-02 | 4.26e-02 | 2.99e-02 |

## Code provenance (work/PROVENANCE)

```
m_mhw commit: a7bdda7ff5a3ab4b5e09c0a1a50b86ef73b0575c
c1e724053340aecc65b383e8e716eb93e5de5ddd9aa717e52955622035578d9f  detectc.m
3c35ac022cbce0b6c1783f4de330cfb52edd5de402c49cdf006d6e0fca03120a  /mnt/volume2/icsa-2027/ref/octave-eq/work/detectc.m
3ee3b4c08fa8edd8f9842d803d2a6d4350355aa5686718054a599888286b5742  /mnt/volume2/icsa-2027/ref/octave-eq/work/movmean_omitnan.m
aa7f8aa2650fee9eccfe25cd95bcb3669545487f76f6e3284238fa88cc735533  /mnt/volume2/icsa-2027/ref/octave-eq/work/nanmax.m
7bd3491f2be8fc724d04dcc84059fd5afeece7538e3a5e0797538bcf2d10ca39  /mnt/volume2/icsa-2027/ref/octave-eq/work/nansum.m
55743f98b186ce8f42b3f7b62d02d24870d8fc530408c9e4f1c99dd8cb3c3360  /mnt/volume2/icsa-2027/ref/octave-eq/work/run_block.m
7e028e68489b96fb54507ef08803d9dca2f94ae07bd14176994bab7ff3148115  /mnt/volume2/icsa-2027/ref/octave-eq/work/t_semantics.m
```
