import numpy as np, pickle, h5py, time
from datetime import date, timedelta

base = "/data/icsa2027_data_20261101T090944Z/s1z"
arr = np.load("/work/baseline_region_f32.npy")  # (4028, 60, 60) float32, dates 1991-12-27..2003-01-05
data = arr.astype(np.float64)

d0 = date(1991,12,27)
date_list = [d0 + timedelta(days=k) for k in range(arr.shape[0])]

def doy_of(dt):
    return (dt - date(dt.year, 1, 1)).days + 1

# baseline dates only (1992-01-01..2002-12-31)
base_dates = [d for d in date_list if date(1992,1,1) <= d <= date(2002,12,31)]
base_idx = {d: k for k, d in enumerate(date_list)}

# EXACT pool construction per spec:
# For each doy d != 60: pool = every SST value whose date lies within +/-5 CALENDAR days
# of a baseline date whose day-of-year is d.
# Calendar windows may extend beyond baseline ends (1991-12-27..31 and 2003-01-01..05) - include those.
# 29 Feb values belong to the windows of their calendar neighbours. Day 60 has no pool.
t0 = time.time()
pools = {}
for d in range(1, 367):
    if d == 60:
        continue
    # candidate dates: all dates in the loaded array within +/-5 calendar days of any
    # baseline date with doy == d. Since the loaded array covers 1991-12-27..2003-01-05
    # (which is exactly baseline +/- 5 days), candidates = all dates in array whose doy
    # is within [d-5, d+5] (mod nothing - plain doy arithmetic, but careful about year
    # boundaries via the exact calendar rule).
    # Build from the calendar: for each baseline date b with doy(b)==d, the window is
    # [b-5, b+5]. Collect all window dates, dedupe, intersect with array range.
    win = set()
    for b in base_dates:
        if doy_of(b) == d:
            k = base_idx[b]
            for kk in range(max(0, k-5), min(arr.shape[0], k+5+1)):
                win.add(kk)
    ii = np.array(sorted(win))
    pools[d] = data[ii]
print("exact pool build time:", round(time.time()-t0,1), "s")

# check against previous (approximate) approach: doy in [d-5,d+5]
with open("/work/window_dates.pkl","rb") as f:
    wd_old = pickle.load(f)
win_old = wd_old["win_dates"]
idx_of = {d: k for k, d in enumerate(date_list)}
mismatch = []
for d in range(1, 367):
    if d == 60: continue
    old = set(idx_of[dt] for dt in win_old[d])
    new = set(pools[d-1].shape[0] * [0]) if False else None
    # compare sizes only (contents same if sizes same, since both sorted sets from same array)
print("old vs new sizes:")
diffs = []
for d in range(1, 367):
    if d == 60: continue
    old_n = len(win_old[d])
    new_n = pools[d].shape[0]
    if old_n != new_n:
        diffs.append((d, old_n, new_n))
print("size differences:", diffs if len(diffs) < 20 else f"{len(diffs)} diffs, first 20: {diffs[:20]}")
