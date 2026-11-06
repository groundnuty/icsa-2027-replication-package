import numpy as np, pickle, time
from datetime import date, timedelta

arr = np.load("/work/baseline_region_f32.npy")   # (4028,60,60) f32, dates 1991-12-27..2003-01-05
data = arr.astype(np.float64)
N = data.shape[0]
d0 = date(1991,12,27)
date_list = [d0 + timedelta(days=k) for k in range(N)]
k_of = {d: k for k, d in enumerate(date_list)}

# month/day doy mapping (leap-style, year-independent)
MD_CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_md(dt): return MD_CUM[dt.month-1] + dt.day

# sanity
assert doy_md(date(1993,12,31)) == 366
assert doy_md(date(1993,3,1)) == 61
assert doy_md(date(1992,2,29)) == 60
assert doy_md(date(1993,2,28)) == 59
print("month/day mapping verified")

base_dates = [d for d in date_list if date(1992,1,1) <= d <= date(2002,12,31)]
print("baseline dates:", base_dates[0], base_dates[-1], len(base_dates))

# calendar-window pools
t0 = time.time()
pool_idx = {}
for d in range(1, 367):
    if d == 60: continue
    win = set()
    for b in base_dates:
        if doy_md(b) == d:
            k = k_of[b]
            for kk in range(max(0, k-5), min(N, k+6)):
                win.add(kk)
    pool_idx[d] = sorted(win)
print("pool build:", round(time.time()-t0,2), "s")

sizes = {d: len(v) for d, v in pool_idx.items()}
import collections
print("pool size distribution:", collections.Counter(sizes.values()))
# expected: 121 for all d != 60 (11 baseline dates x 11-day calendar windows, no overlap)
print("d=1:", sizes[1], " d=59:", sizes[59], " d=61:", sizes[61], " d=366:", sizes[366])
print("d=366 first/last dates:", date_list[pool_idx[366][0]], date_list[pool_idx[366][-1]])
print("d=1 first/last dates:", date_list[pool_idx[1][0]], date_list[pool_idx[1][-1]])
# Feb 29 inclusion in neighbouring pools
for d in [55, 56, 57, 58, 59, 61, 62, 63, 64, 65, 66]:
    feb29 = sum(1 for k in pool_idx[d] if date_list[k].month==2 and date_list[k].day==29)
    print(f"d={d}: pool size {sizes[d]}, Feb29 values: {feb29}")
with open("/work/pool_idx.pkl","wb") as f:
    pickle.dump(pool_idx, f)
