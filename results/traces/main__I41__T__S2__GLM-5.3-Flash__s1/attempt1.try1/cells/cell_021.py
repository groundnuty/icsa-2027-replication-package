import numpy as np, datetime as dt, pickle

# --- Independent re-derivation for a few cells: pools via pandas date arithmetic, joining via pure loop ---
import pandas as pd
B = np.load('work/B.npy').astype(np.float64)      # row0 = 1991-12-27
T = np.load('work/T.npy').astype(np.float64)
thr_s = np.load('work/thr_s.npy')
mhw_mask = np.load('work/mhw_mask.npy')
bdates = pd.date_range('1991-12-27', periods=B.shape[0], freq='D')
tdates = pd.date_range('2021-06-01', periods=92, freq='D')

# special doy via pandas: dayofyear adjusted (+1 after Feb in non-leap)
def sdoy(ts):
    n = ts.dayofyear
    if not ts.is_leap_year and n >= 60: n += 1
    return n
bdoy_s = np.array([sdoy(t) for t in bdates])

def pool_rows(d):
    if d == 60: return None
    rows = set()
    for k in np.where(bdoy_s == d)[0]:
        for off in range(-5, 6):
            q = bdates[k] + pd.Timedelta(days=off)
            rows.add((q - bdates[0]).days)
    return np.array(sorted(rows))

ok_thr = True; ok_clim = True
for d in [1, 59, 61, 92, 153, 200, 244, 300, 366]:
    if d == 60: continue
    rows = pool_rows(d)
    pool = B[rows]
    th_ref = np.nanpercentile(pool, 90, axis=0, method='hazen')
    cl_ref = np.nanmean(pool, axis=0)
    # recompute raw from saved raw arrays
    thr_raw = np.load('work/thr_raw.npy'); clim_raw = np.load('work/clim_raw.npy')
    if not np.allclose(th_ref, thr_raw[d-1], rtol=0, atol=1e-9): ok_thr = False; print("thr mismatch doy", d)
    if not np.allclose(cl_ref, clim_raw[d-1], rtol=0, atol=1e-9): ok_clim = False; print("clim mismatch doy", d)
print("pool/threshold/climatology independent recheck (9 doys):", "OK" if ok_thr and ok_clim else "FAIL")

# independent loop-based joining for a sample of cells
def join_loop(h):
    nt = len(h); mhw = np.zeros(nt, bool)
    i = 0
    # collect all runs (any length) then filter+join
    runs = []
    while i < nt:
        if h[i]:
            j = i
            while j+1 < nt and h[j+1]: j += 1
            runs.append([i, j]); i = j+1
        else:
            i += 1
    cand = [r for r in runs if r[1]-r[0]+1 >= 5]
    if not cand: return mhw
    merged = [cand[0][:]]
    for r in cand[1:]:
        if r[0] - merged[-1][1] - 1 <= 2: merged[-1][1] = r[1]
        else: merged.append(r[:])
    for a, b in merged: mhw[a:b+1] = True
    return mhw

ok_join = True
for (i, j) in [(0,0),(0,39),(15,15),(30,30),(45,45),(59,59),(59,0),(7,52),(22,8),(50,31)]:
    h = np.load('work/hot.npy')[:, i, j]
    if not np.array_equal(join_loop(h), mhw_mask[:, i, j]):
        ok_join = False; print("join mismatch at", (i, j))
print("independent loop-based joining (10 cells):", "OK" if ok_join else "FAIL")

# independent hot recompute for a sample of cells via stored arrays
hot = np.load('work/hot.npy')
ok_hot = True
for (i, j) in [(0,0),(0,39),(30,30),(59,59),(10,25)]:
    th = thr_s[[sdoy(t)-1 for t in tdates], i, j]
    h_ref = np.isfinite(T[:, i, j]) & (T[:, i, j] >= th)
    if not np.array_equal(h_ref, hot[:, i, j]): ok_hot = False
print("independent hot recompute (5 cells):", "OK" if ok_hot else "FAIL")
