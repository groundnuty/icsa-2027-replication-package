# M+ tables: per row n, median, range (seconds; bytes in GB), instance labels in summary_table.json

| row | P s (n, med, range) | placed GB | cold wall s | M+ wall s | cold first-compute s | M+ first-compute s | break-even, wall (PRIMARY) | break-even, first-compute (SECONDARY) |
|---|---|---|---|---|---|---|---|---|
| S1/required/cold-site-f | n=5, med 42.9, 42.6-43.0 | n=5, med 0.50, 0.50-0.50 | n=5, med 452.8, 444.2-460.1 | n=5, med 408.9, 398.5-425.8 | n=5, med 12.7, 12.4-15.7 | n=5, med 12.6, 12.5-12.8 | 2.0 [1.0, 2.0] | 45.0 [20.0, no break-even] |
| S1/required/cold-site-g | n=5, med 42.9, 42.6-43.0 | n=5, med 0.50, 0.50-0.50 | n=3, med 491.2, 469.7-509.1 | n=5, med 408.9, 398.5-425.8 | n=3, med 10.3, 10.2-10.3 | n=5, med 12.6, 12.5-12.8 | 1.0 [1.0, 1.0] | no break-even [no break-even, no break-even] |
| S1/required/cold-wan | n=5, med 42.9, 42.6-43.0 | n=5, med 0.50, 0.50-0.50 | n=3, med 2083.7, 2053.5-2893.7 | n=5, med 408.9, 398.5-425.8 | n=3, med 12.7, 12.6-15.0 | n=5, med 12.6, 12.5-12.8 | 1.0 [1.0, 1.0] | 54.0 [19.0, no break-even] |
| S1/layout/cold-site-f | n=3, med 96.9, 95.1-113.2 | n=3, med 4.25, 4.25-4.25 | n=5, med 452.8, 444.2-460.1 | n=5, med 413.1, 403.0-417.5 | n=5, med 12.7, 12.4-15.7 | n=5, med 12.6, 12.4-13.0 | 3.0 [3.0, 3.0] | 108.0 [47.0, no break-even] |
| S1/layout/cold-site-g | n=3, med 96.9, 95.1-113.2 | n=3, med 4.25, 4.25-4.25 | n=3, med 491.2, 469.7-509.1 | n=5, med 413.1, 403.0-417.5 | n=3, med 10.3, 10.2-10.3 | n=5, med 12.6, 12.4-13.0 | 2.0 [2.0, 2.0] | no break-even [no break-even, no break-even] |
| S1/layout/cold-wan | n=3, med 96.9, 95.1-113.2 | n=3, med 4.25, 4.25-4.25 | n=3, med 2083.7, 2053.5-2893.7 | n=5, med 413.1, 403.0-417.5 | n=3, med 12.7, 12.6-15.0 | n=5, med 12.6, 12.4-13.0 | 1.0 [1.0, 1.0] | 128.0 [46.0, no break-even] |
| S2/required/cold-site-f | n=5, med 11.2, 11.0-11.6 | n=5, med 0.53, 0.53-0.54 | n=5, med 52.0, 51.3-56.5 | n=5, med 37.9, 36.7-39.3 | n=5, med 6.9, 6.8-7.3 | n=5, med 6.7, 6.6-6.8 | 1.0 [1.0, 1.0] | 46.0 [26.0, 96.0] |
| S2/required/cold-site-g | n=5, med 11.2, 11.0-11.6 | n=5, med 0.53, 0.53-0.54 | n=3, med 67.8, 66.8-68.8 | n=5, med 37.9, 36.7-39.3 | n=3, med 5.6, 5.6-5.6 | n=5, med 6.7, 6.6-6.8 | 1.0 [1.0, 1.0] | no break-even [no break-even, no break-even] |
| S2/required/cold-wan | n=5, med 11.2, 11.0-11.6 | n=5, med 0.53, 0.53-0.54 | n=1, med 87.6, 87.6-87.6 | n=5, med 37.9, 36.7-39.3 | n=1, med 9.0, 9.0-9.0 | n=5, med 6.7, 6.6-6.8 | 1.0 [1.0, 1.0] | 6.0 [5.0, 6.0] |
| S2/layout/cold-site-f | n=3, med 26.1, 24.1-28.2 | n=3, med 3.79, 3.79-3.79 | n=5, med 52.0, 51.3-56.5 | n=5, med 38.3, 37.3-39.0 | n=5, med 6.9, 6.8-7.3 | n=5, med 6.7, 6.7-6.7 | 2.0 [2.0, 3.0] | 109.0 [60.0, 224.0] |
| S2/layout/cold-site-g | n=3, med 26.1, 24.1-28.2 | n=3, med 3.79, 3.79-3.79 | n=3, med 67.8, 66.8-68.8 | n=5, med 38.3, 37.3-39.0 | n=3, med 5.6, 5.6-5.6 | n=5, med 6.7, 6.7-6.7 | 1.0 [1.0, 1.0] | no break-even [no break-even, no break-even] |
| S2/layout/cold-wan | n=3, med 26.1, 24.1-28.2 | n=3, med 3.79, 3.79-3.79 | n=1, med 87.6, 87.6-87.6 | n=5, med 38.3, 37.3-39.0 | n=1, med 9.0, 9.0-9.0 | n=5, med 6.7, 6.7-6.7 | 1.0 [1.0, 1.0] | 12.0 [11.0, 13.0] |

SECONDARY (science can drop it): the break-even on time to first compute, P = provisioning seconds, C and W = the cold and the M+ runs' first_compute_s. The registered, primary break-even is on wall time (break_even_wall_primary).
Seed 20271201. client caches fresh per run; provider and storage page caches not controlled. Failed runs are excluded and counted per layout (failed_runs_excluded) in the JSON.
