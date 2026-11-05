# Daily-map agreement on the checksum-verified event maps (issue #4)

> Scope (`SCOPE.md` §2-4): Step B describes the data-version effect on the authors' domain; it is not attached to the production ground truth.
> Every figure here is for **n = 30 of 189 events (checksum-verified files)**, never catalogue-wide.

Published maps: the 30 event files whose size and md5 match the publisher's list, as of 1 Nov 2026 when the downloads were stopped.
Truncated or partial files on disk are not read.
Events: 001, 002, 003, 004, 005, 006, 007, 008, 009, 010, 011, 012, 013, 014, 015, 016, 017, 018, 019, 020, 021, 022, 023, 024, 026, 027, 028, 029, 030, 034.
These are the first events in catalogue order (the download ran in order), all in 1982-1989. They are not a sample of the record:
early winters and the long winter events (up to 243 days) weigh heavily in the pooled figures.

Our maps: the per-cell masks of the Step B run (`stepB_s1read/masks_sha256.txt`). Comparison: `validate.map_agreement`.

| mode | domain | n | Jaccard per event: mean / median / min / max | pooled Jaccard (sum of both over sum of union) | cell-days both / only published / only ours | days exactly equal / event days |
|---|---|---|---|---|---|---|
| (a) published fields | BALarea | 30 | 0.277 / 0.190 / 0.000 / 0.802 | 0.396 | 13420099 / 17843728 / 2629694 | 0 / 1309 |
| (b) computed fields | BALarea | 30 | 0.238 / 0.118 / 0.000 / 0.782 | 0.358 | 12104249 / 19159578 / 2540045 | 0 / 1309 |
| (a) published fields | authors' domain | 30 | 0.277 / 0.190 / 0.000 / 0.802 | 0.396 | 13420099 / 17843728 / 2629694 | 0 / 1309 |
| (b) computed fields | authors' domain | 30 | 0.249 / 0.131 / 0.000 / 0.816 | 0.367 | 12104249 / 19159578 / 1706940 | 0 / 1309 |

## Per event (n = 30)

| event | onset | days | (a) Jaccard BALarea | (b) Jaccard BALarea | (a) Jaccard authors' domain | (b) Jaccard authors' domain |
|---|---|---|---|---|---|---|
| 001 | 1982-01-02 | 7 | 0.260 | 0.000 | 0.260 | 0.000 |
| 002 | 1982-03-30 | 8 | 0.012 | 0.034 | 0.012 | 0.038 |
| 003 | 1982-04-18 | 11 | 0.023 | 0.032 | 0.023 | 0.033 |
| 004 | 1982-05-26 | 5 | 0.010 | 0.000 | 0.010 | 0.000 |
| 005 | 1982-06-01 | 13 | 0.604 | 0.613 | 0.604 | 0.629 |
| 006 | 1982-07-12 | 33 | 0.577 | 0.580 | 0.577 | 0.607 |
| 007 | 1982-09-22 | 243 | 0.426 | 0.335 | 0.426 | 0.345 |
| 008 | 1983-07-05 | 28 | 0.625 | 0.591 | 0.625 | 0.606 |
| 009 | 1983-09-06 | 6 | 0.199 | 0.184 | 0.199 | 0.193 |
| 010 | 1983-09-23 | 5 | 0.056 | 0.043 | 0.056 | 0.049 |
| 011 | 1983-11-03 | 20 | 0.522 | 0.371 | 0.522 | 0.400 |
| 012 | 1983-12-03 | 134 | 0.011 | 0.017 | 0.011 | 0.018 |
| 013 | 1984-04-18 | 23 | 0.008 | 0.001 | 0.008 | 0.001 |
| 014 | 1984-05-14 | 29 | 0.603 | 0.606 | 0.603 | 0.620 |
| 015 | 1984-08-01 | 13 | 0.048 | 0.049 | 0.048 | 0.052 |
| 016 | 1984-09-23 | 243 | 0.519 | 0.499 | 0.519 | 0.514 |
| 017 | 1985-06-03 | 8 | 0.102 | 0.110 | 0.102 | 0.114 |
| 018 | 1985-08-19 | 8 | 0.116 | 0.044 | 0.116 | 0.044 |
| 019 | 1985-11-21 | 153 | 0.182 | 0.040 | 0.182 | 0.041 |
| 020 | 1986-05-04 | 10 | 0.007 | 0.000 | 0.007 | 0.000 |
| 021 | 1986-06-16 | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| 022 | 1986-06-23 | 18 | 0.623 | 0.634 | 0.623 | 0.667 |
| 023 | 1986-11-18 | 182 | 0.092 | 0.054 | 0.092 | 0.054 |
| 024 | 1987-10-25 | 11 | 0.640 | 0.396 | 0.640 | 0.432 |
| 026 | 1988-05-22 | 16 | 0.208 | 0.260 | 0.208 | 0.265 |
| 027 | 1988-06-11 | 49 | 0.802 | 0.782 | 0.802 | 0.816 |
| 028 | 1988-09-07 | 7 | 0.531 | 0.463 | 0.531 | 0.511 |
| 029 | 1988-10-02 | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| 030 | 1988-10-13 | 11 | 0.419 | 0.267 | 0.419 | 0.267 |
| 034 | 1989-07-26 | 5 | 0.090 | 0.126 | 0.090 | 0.149 |
