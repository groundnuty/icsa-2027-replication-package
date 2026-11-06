
import numpy as np

# --- synthetic test of run/merge logic ---
def mhw_runs(h):
    h = np.asarray(h, bool)
    d = np.diff(np.concatenate(([0], h.view(np.int8), [0])))
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1
    merged = []
    for s, e in zip(starts, ends):
        if e - s + 1 >= 5:
            if merged and s - merged[-1][1] - 1 <= 2:
                merged[-1][1] = e
            else:
                merged.append([s, e])
    return merged

T = np.array([1]*6 + [0]*2 + [1]*5 + [0]*3 + [1]*7 + [0]*1 + [1]*4)
print("test1:", mhw_runs(T))  # runs: 0-5(6), 8-12(5), 16-22(7), 24-27(4)
# expect: [0,12] (gap2 merge), [16,22] (gap3 no merge), 24-27 too short
T2 = np.array([1]*5 + [0]*1 + [1]*5)
print("test2:", mhw_runs(T2))  # [0,10]
T3 = np.array([1]*5 + [0]*2 + [1]*5 + [0]*2 + [1]*5)
print("test3:", mhw_runs(T3))  # cascade -> [0,19]
T4 = np.array([1]*5 + [0]*2 + [1]*3 + [0]*1 + [1]*6)
print("test4:", mhw_runs(T4))  # short run between: 5-day runs at 0-4, 9-14(gap: days 5,6 cold=2, then 7,8 hot) -> 0-4 and 9-14 gap = 9-4-1 = 4 -> no merge -> [[0,4],[9,14]]
# verify masks
m = np.zeros(len(T), bool)
for s, e in mhw_runs(T):
    m[s:e+1] = True
print("test1 mask:", m.astype(int).tolist())

# --- spot check threshold for one cell/day, independently ---
import json
from datetime import date, timedelta
buf = np.load('/work/bs.npy')
thr_s = np.load('/work/thr_s.npy')
def get_dates(d0, d1):
    out, cur = [], d0
    while cur <= d1:
        out.append(cur); cur += timedelta(days=1)
    return out
buf_dates = get_dates(date(1991,12,27), date(2003,1,5))
c = 100
d = 170  # June 10 by leap table (cuml: May=152, +18)
# independent collection: baseline dates b with doy(b)=170 -> month/day: cuml[5]=152 -> June; day = 170-152 = 18 -> June 18
vals = []
for y in range(1992, 2003):
    b = date(y, 6, 18)
    for o in range(-5, 6):
        t = b + timedelta(days=o)
        i = buf_dates.index(t)
        vals.append(buf[i, c])
vals = np.array(vals)
q = np.quantile(vals, 0.9, method='hazen')
mean = vals.mean()
# raw (unsmoothed) threshold for this cell/day = thr before smoothing; recompute raw:
print("n:", len(vals), "independent q90:", q, "mean:", mean)
# compare with pre-smoothing array? we saved smoothed only; recompute raw quickly for this cell
pools = {dd: [] for dd in range(1, 367)}
cuml = np.cumsum([0,31,29,31,30,31,30,31,31,30,31,30,31])
def doy(dd): return int(cuml[dd.month-1] + dd.day)
for i, t in enumerate(buf_dates):
    for o in range(-5, 6):
        b = t + timedelta(days=o)
        if date(1992,1,1) <= b <= date(2002,12,31):
            pools[doy(b)].append(i)
X = buf[pools[170]]
print("pools[170] size:", len(pools[170]), "matches manual:", np.allclose(np.sort(X[:, c]), np.sort(vals)))
print("raw q90 cell100 d170:", np.quantile(X[:, c], 0.9, method='hazen'))
