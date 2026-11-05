# Round trip of the SST reconstruction under the authors' export (issue #4)

> Scope (`SCOPE.md` §2): this tests the reconstruction (map + mclim at the labelled day of year) on the authors' own export, as executed by GNU Octave 9.2.0, on one block over the whole record. It does not test the authors' input data.

All Step_4 time labels were checked to sit at 12:00 UTC.

Block lat 568:588, lon 800:820; input S1 (sha256 in source.json), 1982-01-01..2023-12-30.
The authors' Step_2, Step_3 and Step_4 ran under GNU Octave 9.2.0 (tools/octave/run_export.m).
Result: 130 events and 6964 event days in the block; 1365234 map cell-days.

Pass criterion: every rebuilt cell-day within 1.53e-05 K (half a float32 ulp at 256-512 K) of the input SST of its labelled day.

| check | cell-days | max abs d (K) | share within half an ulp |
|---|---|---|---|
| rebuild | 1365234 | 0 | 1.0000 |
| control: previous day's SST | 1365234 | 6.83 | 0.7559 |
| control: day of year + 1 | 1365234 | 0.323 | 0.4663 |

| labelled day | cell-days | max abs d (K) |
|---|---|---|
| 1982-01-02 (record start) | 65 | 0 |
| 29 February | 2454 | 0 |
| 31 Dec / 1 Jan | 6304 | 0 |

A control fails when it does not meet the criterion (not every cell-day within half an ulp).
Under sea ice the SST stays at a constant freezing value for days, so in an ice block a large share of
cell-days also matches the previous day: the shares below 1 and the large maxima are what show the failure.

Round trip PASSES: the rebuild returns the input SST on every map cell-day, the labelled special days included; both controls fail as they must (shares 0.7559 and 0.4663).
