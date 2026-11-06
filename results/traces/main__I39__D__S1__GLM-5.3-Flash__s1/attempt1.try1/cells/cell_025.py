import numpy as np, datetime as dt, warnings
warnings.filterwarnings('ignore')

coords = np.load('/work/coords.npz', allow_pickle=True)
time_ext = coords['time_ext']; time_tgt = coords['time_tgt']
sst_ext = np.load('/work/sst_ext.npy'); sst_tgt = np.load('/work/sst_tgt.npy')
thr = np.load('/work/thr.npy'); mhw = np.load('/work/mhw.npy')

ci, ck = 15, 15   # sample sea cell
# --- pure-python independent pipeline for this cell ---
ext_dates = [np.datetime64(t,'D').astype(dt.date) for t in time_ext]
ext_vals = sst_ext[:, ci, ck].astype(np.float64)
cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])

def pools(d):
    m = None
    # find (m,dd) for doy d
    for mi in range(12):
        if cum[mi] < d <= cum[mi+1]:
            m, dd = mi+1, d - cum[mi]; break
    base = set()
    for y in range(1992, 2003):
        c = dt.date(y, m, dd)
        for off in range(-5, 6):
            base.add(c + dt.timedelta(days=off))
    vals = [v for v, x in zip(ext_vals, ext_dates) if x in base and np.isfinite(v)]
    return vals

def hazen(vals, p=0.9):
    v = np.sort(np.asarray(vals, dtype=np.float64))
    m = len(v)
    h = m*p + 0.5
    lo = int(np.floor(h)); hi = int(np.ceil(h))
    lo = max(1, min(m, lo)); hi = max(1, min(m, hi))
    return float(v[lo-1] + (h-lo)*(v[hi-1]-v[lo-1]))

thr_raw_p = np.full(366, np.nan); clim_raw_p = np.full(366, np.nan)
for d in list(range(1, 60)) + list(range(61, 367)):
    vals = pools(d)
    thr_raw_p[d-1] = hazen(vals)
    clim_raw_p[d-1] = float(np.mean(vals))
thr_raw_p[59] = 0.5*(thr_raw_p[58] + thr_raw_p[60])
clim_raw_p[59] = 0.5*(clim_raw_p[58] + clim_raw_p[60])

def smooth(arr):
    return np.array([np.mean([arr[(d+off) % 366] for off in range(-15,16)]) for d in range(366)])

thr_p = smooth(thr_raw_p); clim_p = smooth(clim_raw_p)

# compare with vectorized results
d_thr = np.max(np.abs(thr_p - thr[:, ci, ck]))
d_clim = np.max(np.abs(clim_p - clim[:, ci, ck]))
print('cell (15,15): max |thr diff| =', d_thr, '| max |clim diff| =', d_clim)

# independent MHW check for this cell
tgt_dates = [np.datetime64(t,'D').astype(dt.date) for t in time_tgt]
tgt_vals = sst_tgt[:, ci, ck].astype(np.float64)
hot_p = np.array([v >= thr_p[cum[x.month-1]+x.day-1] for v, x in zip(tgt_vals, tgt_dates)])
runs = []
j = 0
while j < 92:
    if hot_p[j]:
        e = j
        while e+1 < 92 and hot_p[e+1]: e += 1
        if e-j+1 >= 5: runs.append([j,e])
        j = e+1
    else: j += 1
merged = []
for s,e in runs:
    if merged and s-merged[-1][1]-1 <= 2: merged[-1][1] = e
    else: merged.append([s,e])
mhw_p = np.zeros(92, dtype=np.uint8)
for s,e in merged: mhw_p[s:e+1] = 1
print('cell (15,15): independent mhw == saved mask:', bool(np.array_equal(mhw_p, mhw[:, ci, ck])))
print('cell (15,15): merged runs (target-index):', merged)
