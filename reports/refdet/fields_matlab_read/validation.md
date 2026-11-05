# Reference detector validation (issue #4)

Run: 2026-10-31T21:27:29, raw SST product version/time: Version 2.0, created 20250117T143312Z

## Mode (b) fields vs published m90 / mclim

- m90: max abs diff 3.523e+00 K, mean 1.484e-01 K over 58199124 cell-days; upper bounds of diff quantiles {'p50': 0.1778279410038923, 'p90': 0.31622776601683794, 'p99': 3.1622776601683795}; NaN only ours 90402, NaN only published 9598350, published-finite cells outside our sea mask 0
- mclim: max abs diff 2.548e+00 K, mean 1.158e-01 K over 58199124 cell-days; upper bounds of diff quantiles {'p50': 0.1, 'p90': 0.31622776601683794, 'p99': 3.1622776601683795}; NaN only ours 90402, NaN only published 9598350, published-finite cells outside our sea mask 0

## Percentile estimator candidates (full pipeline, sample of sea cells), diff vs published m90

| estimator | max abs | mean abs |
|---|---|---|
| interpolated_inverted_cdf | 3.359e+00 | 1.333e-01 |
| linear | 3.356e+00 | 1.352e-01 |
| inverted_cdf | 3.356e+00 | 1.352e-01 |
| averaged_inverted_cdf | 3.356e+00 | 1.352e-01 |
| closest_observation | 3.356e+00 | 1.352e-01 |
| lower | 3.356e+00 | 1.352e-01 |
| higher | 3.356e+00 | 1.352e-01 |
| midpoint | 3.356e+00 | 1.352e-01 |
| nearest | 3.356e+00 | 1.352e-01 |
| hazen | 3.297e+00 | 1.483e-01 |
| matlab_formula | 3.297e+00 | 1.483e-01 |
| normal_unbiased | 3.283e+00 | 1.529e-01 |
| median_unbiased | 3.278e+00 | 1.545e-01 |
| weibull | 3.239e+00 | 1.688e-01 |
