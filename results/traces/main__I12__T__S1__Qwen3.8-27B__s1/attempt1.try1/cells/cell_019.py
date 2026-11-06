import numpy as np, datetime as dt
z = np.load('data/climthr.npz')
thr_raw = z['thr_raw']; sea = z['sea']
SST_win = np.load('data/SST_win.npy')
rng = np.random.default_rng(7)

def daterange(a, b):
    d = a
    while d <= b:
        yield d; d += dt.timedelta(days=1)
win_dates = list(daterange(dt.date(1991,12,27), dt.date(2003,1,5)))
base_start = dt.date(1992,1,1); base_end = dt.date(2002,12,31)
def doy(d): return (d.replace(year=2000) - dt.date(2000,1,1)).days + 1
def q_type4(x, p):  # MATLAB default / HF type 4
    x = np.sort(x); n = len(x)
    h = (n-1)*p; lo = int(np.floor(h)); hi = int(np.ceil(h))
    return x[lo] if lo==hi else x[lo] + (h-lo)*(x[hi]-x[lo])

worst = 0.0
for trial in range(60):
    c, l = int(rng.integers(0,60)), int(rng.integers(0,60))
    if not sea[c,l]: continue
    d = int(rng.integers(1,367))
    if d == 60: continue
    idxs = []
    for i, wdt in enumerate(win_dates):
        if base_start <= wdt <= base_end and doy(wdt) == d:
            idxs.extend(range(max(0,i-5), min(len(win_dates), i+6)))
    pool = SST_win[idxs, c, l]; pool = pool[np.isfinite(pool)]
    assert len(pool) == 121
    manual4 = q_type4(pool, 0.9)
    # pipeline's raw used hazen (type 2); compare pool & climatology exactly, and quantile type4 vs manual
    a4 = np.quantile(pool, 0.9, method='linear')
    assert a4 == manual4
    clim_manual = pool.mean()
    # recompute climatology from pipeline raw? clim_raw is stored; verify
    cmine = z['clim_raw'][d-1, c, l]
    worst = max(worst, abs(cmine - clim_manual))
print('max diff climatology vs manual pool mean (60 checks):', worst)
# pools identical? verify one raw thr with manual type2 (hazen)
manual2 = np.quantile(pool, 0.9, method='hazen')
print('raw thr (hazen) equals manual hazen:', manual2 == thr_raw[d-1, c, l])