# Null distribution for the Step B overlap count (issue #4)

> Scope (`SCOPE.md` §2-4): Step B describes the data-version effect on the authors' domain; it is not attached to the production ground truth.

1000 draws, seed 20261101. Each draw places 189 synthetic events with the published durations (1 to 469 days, median 18) uniformly at random within 1982-01-02..2023-12-30, independently.
Observed values use the same active days and the same overlap and exact-match rules as the Step B report.

| detection | active days (of 15,338) | observed overlapped | null overlapped: mean [2.5 %, 97.5 %] | P(null >= observed) | observed exact onset+end | null exact: mean [2.5 %, 97.5 %] | P(null >= observed) |
|---|---|---|---|---|---|---|---|
| mode b, BALarea | 12288 | 179 | 172.8 [165, 180] | 0.058 | 21 | 0.0 [0, 1] | 0.000 |
| mode a, BALarea | 11872 | 181 | 171.5 [163, 179] | 0.006 | 20 | 0.0 [0, 1] | 0.000 |
| mode b, authors' domain | 12271 | 179 | 172.8 [165, 180] | 0.056 | 20 | 0.0 [0, 1] | 0.000 |

Reading:
- The overlap count is close to its chance level, because most days are active somewhere in the basin. On its own it says little.
- The exact onset+end matches are the informative number; compare the observed value with the null.
- P values are the share of draws at or above the observed value. A value of 0.000 means none of the draws reached it.
