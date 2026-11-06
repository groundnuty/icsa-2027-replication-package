import numpy as np, json
from collections import Counter

PREF = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy(dates):
    dates = dates.astype("datetime64[D]")
    d = dates.astype("int64")
    first = dates.astype("datetime64[M]").astype("datetime64[D]").astype("int64")
    day = d - first + 1
    month = dates.astype("datetime64[M]").astype("int64") % 12
    return PREF[month] + day

X = np.load("/tmp/X.npy"); p3 = np.load("/tmp/p3.npy"); sea = np.load("/tmp/sea.npy"); M = np.load("/tmp/M.npy")
thr_s = np.load("/tmp/thr_s.npy"); mhw = np.load("/tmp/mhw.npy").astype(bool)
cand = np.datetime64("1991-12-27") + np.arange(X.shape[0])

# --- A) hazen quantile independent check ---
def hazen_ref(x, p=0.9):
    x = np.sort(x); n = len(x)
    h = (n + 1) * p - 1.0
    i = int(np.floor(h)); f = h - i
    if i >= n - 1: return x[-1]
    return x[i] + f * (x[i+1] - x[i])
rng = np.random.default_rng(0)
ok = True
for n in [3, 7, 11, 121, 124, 131]:
    x = rng.normal(285, 3, n)
    a = np.quantile(x, 0.9, method="hazen"); b = hazen_ref(x)
    if abs(a - b) > 1e-12: ok = False; print("MISMATCH n=", n, a, b)
print("A) hazen quantile check:", "PASS" if ok else "FAIL")

# --- B) run+merge logic vs naive reference on synthetic patterns ---
def cell_mhw_ref(hot):
    n = len(hot); inrun = np.zeros(n, bool)
    i = 0
    while i < n:
        if hot[i]:
            j = i
            while j + 1 < n and hot[j+1]: j += 1
            runs = []
            if j - i + 1 >= 5: runs.append([i, j])
            i = j + 1
        else: i += 1
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2: merged[-1][1] = e
        else: merged.append([s, e])
    for s, e in merged: inrun[s:e+1] = True
    return inrun

rng = np.random.default_rng(1)
ok = True
for trial in range(2000):
    hot = rng.random(92) < rng.uniform(0.05, 0.6)
    # replicate fast method
    hpad = np.array([False] + list(hot) + [False])
    d = np.diff(hpad.astype(np.int8))
    starts = np.where(d == 1)[0]; ends = np.where(d == -1)[0]
    runs = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2: merged[-1][1] = e
        else: merged.append([s, e])
    fast = np.zeros(92, bool)
    for s, e in merged: fast[s:e+1] = True
    if not np.array_equal(fast, cell_mhw_ref(hot)): ok = False; print("MISMATCH trial", trial); break
print("B) run+merge logic check:", "PASS" if ok else "FAIL")

# --- C) end-to-end single (cell, doy) check ---
c = 0
d = 200  # 19 Jul
pool_idx = np.where(M[d-1])[0]
vals = X[pool_idx, c]
vals = vals[np.isfinite(vals)]
print("C) pool size for doy %d: %d (finite %d)" % (d, len(pool_idx), len(vals)))
thr_raw = hazen_ref(vals)
clim_raw = vals.mean()
# unsmoothed arrays
Xsea = X[:, sea]
thr_u = np.full(366, np.nan)
for dd in range(1, 367):
    if dd == 60: continue
    v = Xsea[M[dd-1], c]; v = v[np.isfinite(v)]
    thr_u[dd-1] = hazen_ref(v)
thr_u[59] = (thr_u[58] + thr_u[60]) / 2
thr_u_s = np.array([thr_u[(d-15+i) % 366].mean() for d in range(1, 367)])
print("C) raw thr (ref): %.6f | stored thr_s[doy200]: %.6f" % (thr_raw, thr_s[199, c]))
print("C) smoothed thr (ref): %.6f" % thr_u_s[199])
assert abs(thr_u_s[199] - thr_s[199, c]) < 1e-9
print("C) PASS")

# --- D) daily active pattern ---
tdates = np.datetime64("2009-06-01") + np.arange(92)
active = mhw.any(axis=1)
line = ""
for i in range(92):
    line += "#" if active[i] else "."
print("D) active pattern Jun-Aug 2009:")
print(line)
