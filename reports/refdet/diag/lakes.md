# Finite cells outside BALarea: lakes, coastal water or open sea (issue #4)

Finite set: S1 SST finite on every day of 1991-12-27..2003-01-05, from the validated S1 field cache (built 2026-11-01T04:13:48+00:00).
It holds 185239 cells. BALarea holds 170171 cells; 166033 are in both.
Finite outside BALarea: 19206 cells in 1489 components (8-connectivity). BALarea cells that are not finite: 4138.

| class | components | cells |
|---|---|---|
| lake | 126 | 2672 |
| coastal/lagoon | 1358 | 2778 |
| open sea | 5 | 13756 |

The definitions are in the script's docstring.
A lake joined to the sea at this resolution counts as coastal/lagoon; such cases are named in the coastal table below.

## Lakes, largest first (all lakes with at least 20 cells; the full list is in the CSV)

| size (cells) | centroid lat | centroid lon | likely name |
|---|---|---|---|
| 1821 | 58.91 | 13.30 | Vänern |
| 574 | 58.33 | 14.54 | Vättern |
| 43 | 64.49 | 11.25 | Snåsavatnet |

## Coastal/lagoon and open-sea components with at least 50 cells

| class | size (cells) | centroid lat | centroid lon | likely name |
|---|---|---|---|---|
| open sea | 13750 | 65.05 | 10.33 |  |
| coastal/lagoon | 214 | 57.85 | 9.02 |  |
| coastal/lagoon | 194 | 56.83 | 9.15 | Limfjord |

## #5 instance boxes (60 x 60 cells)

Counts are of baseline-finite cells. Each instance also needs finiteness on its target days (`box_domains.md`).

| region | lat | lon | finite cells | lake cells | lake components (likely names) | coastal/lagoon cells outside BALarea | open-sea cells |
|---|---|---|---|---|---|---|---|
| R00 | 54.15..55.35 | 13.29..14.49 | 3344 | 0 | 0 (-) | 36 | 0 |
| R01 | 54.17..55.37 | 14.65..15.85 | 3359 | 0 | 0 (-) | 10 | 0 |
| R02 | 54.27..55.47 | 18.57..19.77 | 3343 | 1 | 1 (unnamed) | 32 | 0 |
| R03 | 54.55..55.75 | 16.35..17.55 | 3361 | 0 | 0 (-) | 39 | 0 |
| R04 | 55.15..56.35 | 19.97..21.17 | 3341 | 0 | 0 (-) | 24 | 0 |
| R05 | 55.83..57.03 | 10.71..11.91 | 3364 | 0 | 0 (-) | 12 | 0 |
| R06 | 56.31..57.51 | 18.43..19.63 | 3344 | 0 | 0 (-) | 14 | 0 |
| R07 | 56.71..57.91 | 17.11..18.31 | 3342 | 0 | 0 (-) | 19 | 0 |
| R08 | 56.91..58.11 | 20.41..21.61 | 3345 | 0 | 0 (-) | 2 | 0 |
| R09 | 57.03..58.23 | 10.43..11.63 | 3334 | 0 | 0 (-) | 28 | 0 |
| R10 | 57.25..58.45 | 23.09..24.29 | 3350 | 6 | 2 (unnamed) | 8 | 0 |
| R11 | 57.53..58.73 | 18.69..19.89 | 3347 | 1 | 1 (unnamed) | 20 | 0 |
| R12 | 57.77..58.97 | 9.09..10.29 | 3345 | 0 | 0 (-) | 16 | 0 |
| R13 | 58.77..59.97 | 18.77..19.97 | 3347 | 0 | 0 (-) | 44 | 0 |
| R14 | 58.95..60.15 | 21.43..22.63 | 3341 | 1 | 1 (unnamed) | 64 | 0 |
| R15 | 59.09..60.29 | 20.15..21.35 | 3360 | 1 | 1 (unnamed) | 55 | 0 |
| R16 | 60.15..61.35 | 18.79..19.99 | 3360 | 0 | 0 (-) | 20 | 0 |
| R17 | 60.47..61.67 | 17.37..18.57 | 3352 | 0 | 0 (-) | 15 | 0 |
| R18 | 61.19..62.39 | 20.29..21.49 | 3356 | 0 | 0 (-) | 19 | 0 |
| R19 | 61.81..63.01 | 18.01..19.21 | 3355 | 2 | 2 (unnamed) | 15 | 0 |
| R20 | 62.55..63.75 | 19.71..20.91 | 3351 | 0 | 0 (-) | 15 | 0 |
| R21 | 63.69..64.89 | 21.19..22.39 | 3349 | 5 | 3 (unnamed) | 8 | 0 |
| R22 | 63.83..65.03 | 9.05..10.25 | 3346 | 1 | 1 (unnamed) | 0 | 3345 |
| R23 | 64.13..65.33 | 22.95..24.15 | 3362 | 0 | 0 (-) | 5 | 0 |
| R24 | 64.69..65.89 | 10.25..11.45 | 3348 | 5 | 3 (unnamed) | 0 | 3343 |

Boxes containing lake cells: 9 of 25: R02 (1), R10 (6), R11 (1), R14 (1), R15 (1), R19 (2), R21 (5), R22 (1), R24 (5).
