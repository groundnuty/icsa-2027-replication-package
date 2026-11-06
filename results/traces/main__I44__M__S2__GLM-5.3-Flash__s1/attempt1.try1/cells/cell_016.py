import numpy as np, time
from datetime import date, timedelta
from collections import defaultdict

block = np.load("/tmp/sst_block.npy")
alldays = open("/tmp/alldays.txt").read().split("\n")
nb = 4028
base = block[:nb].astype(np.float64)

idx_of = {s: i for i, s in enumerate(alldays)}
cum_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_of_date(dt):
    return cum_before[dt.month-1] + dt.day

baseline_dates = [date(1992,1,1)+timedelta(days=i) for i in range((date(2002,12,31)-date(1992,1,1)).days+1)]
anchors = defaultdict(list)
for b in baseline_dates:
    anchors[doy_of_date(b)].append(b)

pool_masks = {}
t0 = time.time()
for d in range(1, 367):
    if d == 60: continue
    mask = np.zeros(nb, dtype=bool)
    for b in anchors[d]:
        o = b.toordinal()
        for off in range(-5, 6):
            i = idx_of.get((date.fromordinal(o+off)).isoformat())
            if i is not None: mask[i] = True
    pool_masks[d] = mask
print("built in", round(time.time()-t0, 2), "s; pool sizes:",
      min(m.sum() for m in pool_masks.values()), max(m.sum() for m in pool_masks.values()))

def dates_of(d):
    return [alldays[i] for i in np.flatnonzero(pool_masks[d])]

d366 = dates_of(366)
print("pool 366: n =", len(d366), "| 1992-01-03?", "1992-01-03" in d366,
      "| 1991-12-31?", "1991-12-31" in d366, "| 2003-01-05?", "2003-01-05" in d366,
      "| 2002-12-31?", "2002-12-31" in d366)
d1m = dates_of(1)
print("pool 1: | 2002-12-31?", "2002-12-31" in d1m, "| 1991-12-27?", "1991-12-27" in d1m,
      "| 1992-01-01?", "1992-01-01" in d1m, "| 2002-01-06?", "2002-01-06" in d1m)
print("pool 59 has 1992-02-29?", "1992-02-29" in dates_of(59))
print("pool 61 has 1996-02-29?", "1996-02-29" in dates_of(61))
print("pool 55 has 1992-02-29?", "1992-02-29" in dates_of(55))
print("pool 65 has 2000-02-29?", "2000-02-29" in dates_of(65))

# fast ordinal version must be identical
ordinals = np.array([date.fromisoformat(s).toordinal() for s in alldays[:nb]])
def md_of_doy(d):
    m = 1
    while m < 12 and cum_before[m] < d: m += 1
    return m, d - cum_before[m-1]
fast_ok = True
for d in [1, 2, 59, 61, 153, 244, 365, 366]:
    m, dd = md_of_doy(d)
    mask2 = np.zeros(nb, dtype=bool)
    for y in range(1992, 2003):
        try: a = date(y, m, dd).toordinal()
        except ValueError: continue
        mask2 |= (ordinals >= a-5) & (ordinals <= a+5)
    if not np.array_equal(mask2, pool_masks[d]): fast_ok = False; print("MISMATCH pool", d)
print("fast ordinal pools identical:", fast_ok)
np.save("/tmp/pool_sizes.npy", np.array([pool_masks[d].sum() for d in range(1,367)]))
