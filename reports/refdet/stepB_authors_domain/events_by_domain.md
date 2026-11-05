# Step B events on two domains (issue #4)

> Scope (`SCOPE.md` §2-4): the differences are consistent with the 202506 product-version change, not shown to be caused by it; Step B uses the authors' domain, not the production sea-cell rule; quote as "21/189 exact onset and end; 179/189 published events temporally overlapped" (computed mode, BALarea).

Per-cell masks from /mnt/volume2/icsa-2027/refdet/stepB (Step B run, commit 411ee03). The domain event rule is re-applied on:
- BALarea, the bathymetry mask of the Step B run: 170171 cells;
- the authors' effective domain, where the published m90 is finite: 159261 cells.

Two causes separate:
- (b) on the authors' domain vs (b) on BALarea gives the domain effect;
- (a) vs (b) on the authors' domain holds the SST fixed (ours) and changes only the thresholds: the **threshold effect**.
- The **SST effect** is (a) against the published events: the published thresholds are fixed and the SST changes.

| mode | domain | events | exact onset+end (of 189) | published overlapped | by several | ours overlapping none | active days | onset offset bins | end offset bins |
|---|---|---|---|---|---|---|---|---|---|
| a | BALarea | 186 | 20 | 181 | 23 | 26 | 11872 | {'-10': 51, '-9': 3, '-8': 2, '-6': 2, '-5': 1, '-4': 1, '-3': 6, '-2': 11, '-1': 13, '0': 50, '1': 14, '2': 4, '3': 3, '4': 5, '5': 1, '6': 3, '7': 1, '8': 2, '9': 1, '10': 7} | {'-10': 10, '-7': 2, '-5': 1, '-4': 4, '-3': 2, '-2': 8, '-1': 12, '0': 52, '1': 18, '2': 7, '3': 4, '4': 2, '5': 2, '7': 3, '8': 4, '10': 50} |
| a | authors_domain | 186 | 20 | 181 | 23 | 26 | 11872 | {'-10': 51, '-9': 3, '-8': 2, '-6': 2, '-5': 1, '-4': 1, '-3': 6, '-2': 11, '-1': 13, '0': 50, '1': 14, '2': 4, '3': 3, '4': 5, '5': 1, '6': 3, '7': 1, '8': 2, '9': 1, '10': 7} | {'-10': 10, '-7': 2, '-5': 1, '-4': 4, '-3': 2, '-2': 8, '-1': 12, '0': 52, '1': 18, '2': 7, '3': 4, '4': 2, '5': 2, '7': 3, '8': 4, '10': 50} |
| b | BALarea | 154 | 21 | 179 | 18 | 15 | 12288 | {'-10': 65, '-9': 1, '-8': 1, '-7': 1, '-6': 1, '-3': 3, '-2': 9, '-1': 11, '0': 52, '1': 15, '2': 8, '3': 1, '4': 3, '5': 1, '6': 1, '10': 6} | {'-10': 8, '-8': 3, '-7': 1, '-6': 4, '-4': 3, '-3': 4, '-2': 8, '-1': 10, '0': 48, '1': 12, '2': 5, '4': 6, '5': 2, '6': 2, '7': 2, '8': 1, '9': 1, '10': 59} |
| b | authors_domain | 154 | 20 | 179 | 18 | 14 | 12271 | {'-10': 64, '-9': 1, '-8': 1, '-7': 1, '-6': 1, '-3': 3, '-2': 8, '-1': 11, '0': 53, '1': 15, '2': 8, '3': 1, '4': 3, '5': 2, '6': 1, '10': 6} | {'-10': 8, '-8': 3, '-7': 1, '-6': 4, '-4': 3, '-3': 4, '-2': 8, '-1': 11, '0': 48, '1': 12, '2': 5, '4': 6, '5': 2, '6': 2, '7': 3, '8': 2, '10': 57} |

Check: active days recomputed on BALarea equal the Step B run's own: mode a True, mode b True

Offsets are ours minus published, in days, clipped to plus or minus 10, for each published event against the overlapping one of ours with the largest overlap.
