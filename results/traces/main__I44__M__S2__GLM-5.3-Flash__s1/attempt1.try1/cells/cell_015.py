import numpy as np, time
from datetime import date, timedelta

block = np.load("/tmp/sst_block.npy")
alldays = open("/tmp/alldays.txt").read().split("\n")
sea_cells = np.load("/tmp/sea_cells.npy")
nb = 4028
base = block[:nb].astype(np.float64)

ord_of = {s: date.fromisoformat(s).toordinal() for s in alldays}
idx_of = {s: i for i, s in enumerate(alldays)}

# brute-force spec pools (reference): pool d = union over baseline dates b (1992..2002)
# with doy(b)==d of [b-5, b+5]; doy by month/day mapping (Feb29=60, Mar1=61, Dec31=366)
cum_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def md_of_doy(d):
    m = 1
    while m < 12 and cum_before[m] < d: m += 1
    return m, d - cum_before[m-1]
def doy_of_date(dt):
    return cum_before[dt.month-1] + dt.day

baseline_dates = [date(1992,1,1)+timedelta(days=i) for i in range((date(2002,12,31)-date(1992,1,1)).days+1)]
from collections import defaultdict
anchors = defaultdict(list)
for b in baseline_dates:
    anchors[doy_of_date(b)].append(b)

# calendar-window pools, vectorised: for pool d, union of windows of anchors
pool_masks = {}
t0 = time.time()
for d in range(1, 367):
    if d == 60: continue
    mask = np.zeros(nb, dtype=bool)
    for b in anchors[d]:
        o = b.toordinal()
        for off in range(-5, 6):
            s = (date.fromordinal(o+off)).isoformat()
            i = idx_of.get(s)
            if i is not None: mask[i] = True
    pool_masks[d] = mask
print("built", time.time()-t0, "s; pool sizes:", min(m.sum() for m in pool_masks.values()), max(m.sum() for m in pool_masks.values()))

# cross-check vectorised pools vs a fast ordinal-based construction & spot-check specifics
d366 = pool_masks[366]
dates366 = [alldays[i] for i in np.flatnonzero(d366)]
print("pool 366: n =", len(dates366), "has 1992-01-03?", "1992-01-03" in dates366,
      "has 1991-12-31?", "1991-12-31" in dates366, "has 2003-01-05?", "2003-01-05" in dates366,
      "has 2002-12-31?", "2002-12-31" in dates366)
d1 = pool_masks[1]
dates1 = [alldays[i] for i in np.flatnonzero(d1)]
print("pool 1: has 2002-12-31?", "2002-12-31" in dates1, "has 1991-12-27?", "1991-12-27" in dates1,
      "has 1992-01-01?", "1992-01-01" in dates1, "has 2002-01-06?", "2002-01-06" in dates1)
# Feb29 in neighbour pools
d59 = pool_masks[59]; d61 = pool_masks[61]
print("pool 59 has 1992-02-29?", "1992-02-29" in [alldays[i] for i in np.flatnonzero(d59)])
print("pool 61 has 1996-02-29?", "1996-02-29" in [alldays[i] for i in np.flatnonzero(d61)])
print("pool 65 has 2000-02-29?", "2000-02-29" in [alldays[i] for i in np.flatnonzero(d65)])
print("pool 55 has 1992-02-29?", "1992-02-29" in [alldays[i] for i in np.flatnonzero(d55 := pool_masks[55])])

# fast ordinal version to confirm identical
ordinals = np.array([ord_of[s] for s in alldays[:nb]])
fast_ok = True
for d in [1, 2, 59, 60, 61, 153, 244, 365, 366]:
    if d == 60: continue
    m, dd = md_of_doy(d)
    mask2 = np.zeros(nb, dtype=bool)
    for y in range(1992, 2003):
        try: a = date(y, m, dd).toordinal()
        except ValueError: continue
        mask2 |= (ordinals >= a-5) & (ordinals <= a+5)
    if not np.array_equal(mask2, pool_masks[d]): fast_ok = False; print("MISMATCH pool", d)
print("fast ordinal pools identical:", fast_ok)
np.save("/tmp/pool_sizes.npy", np.array([pool_masks[d].sum() for d in range(1,367)]))
