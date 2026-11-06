import numpy as np, datetime as dt
z = np.load('data/climthr.npz')
thr_raw, clim_raw = z['thr_raw'], z['clim_raw']
thr_smooth, clim_smooth, sea, tgt_doy = z['thr_smooth'], z['clim_smooth'], z['sea'], z['tgt_doy']
SST_win = np.load('data/SST_win.npy')
rng = np.random.default_rng(42)

def daterange(a, b):
    d = a
    while d <= b:
        yield d; d += dt.timedelta(days=1)
win_dates = list(daterange(dt.date(1991,12,27), dt.date(2003,1,5)))
base_start = dt.date(1992,1,1); base_end = dt.date(2002,12,31)
def doy(d): return (d.replace(year=2000) - dt.date(2000,1,1)).days + 1

# --- independent pool construction: for date t, contribute to pools of doys of dates within 5d in baseline
# verify by direct definition: pool(d) = { SST_win[i, cell] : i in window-range, |win_dates[i] - b| <= 5 for some baseline b with doy(b)=d }
def matlab_quantile(x, q):
    x = np.sort(x)
    n = len(x)
    h = (n-1)*q
    lo = int(np.floor(h)); hi = int(np.ceil(h))
    return x[lo] + (h-lo)*(x[hi]-x[lo]) if hi != lo else x[lo]

worst = 0.0
for trial in range(40):
    c, l = int(rng.integers(0,60)), int(rng.integers(0,60))
    if not sea[c,l]: continue
    d = int(rng.integers(1,367))
    if d == 60: continue
    # find anchors: baseline dates with doy == d
    idxs = []
    for i, wdt in enumerate(win_dates):
        if wdt < base_start or wdt > base_end: continue
        if doy(wdt) == d:
            for k in range(-5, 6):
                j = i + k
                if 0 <= j < len(win_dates):
                    idxs.append(j)
    pool = SST_win[idxs, c, l]
    pool = pool[np.isfinite(pool)]
    thr_manual = matlab_quantile(pool, 0.9) if len(pool) else np.nan
    clim_manual = pool.mean() if len(pool) else np.nan
    a, b = thr_raw[d-1, c, l], clim_raw[d-1, c, l]
    assert np.isfinite(a) and np.isfinite(b)
    err = max(abs(a-thr_manual), abs(b-clim_manual))
    worst = max(worst, err)
    assert len(pool) == 121, len(pool)
print('max abs diff (raw thr/clim, 40 random checks):', worst)

# smoothing check, manual loop
worst = 0.0
for trial in range(20):
    c, l = int(rng.integers(0,60)), int(rng.integers(0,60))
    if not sea[c,l]: continue
    i = int(rng.integers(0,366))
    w = [thr_raw[(i+k) % 366, c, l] for k in range(-15, 16)]
    sm = np.mean(w)
    worst = max(worst, abs(sm - thr_smooth[i, c, l]))
print('max abs diff (smooth thr, 20 checks):', worst)

# hazen == MATLAB quantile on synthetic data
x = rng.uniform(size=121)
print('hazen vs manual:', np.nanquantile(x, 0.9, method='hazen'), matlab_quantile(x, 0.9))