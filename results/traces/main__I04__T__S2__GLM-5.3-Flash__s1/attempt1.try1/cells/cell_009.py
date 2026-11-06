import numpy as np, os, json, time as tm, warnings

t_start = tm.time()
win32 = np.load('/tmp/win.npy')                      # (4028,60,60) float32, 1991-12-27..2003-01-05
wd   = np.load('/tmp/dates.npy')[3647:7675]
tgt  = np.load('/tmp/tgt.npy')                       # (92,60,60) float64, 2020-06-01..2020-08-31
sea2d = np.load('/tmp/finite_all_t.npy')             # (60,60) bool: finite on all target days

win = win32.astype(np.float64)
nsea = int(sea2d.sum())
sea_flat = np.flatnonzero(sea2d.ravel())
winf = win.reshape(4028, -1)[:, sea_flat]            # (4028, nsea)
wd_int = wd.astype('int64')

# day-of-year (1..366) -> (month, day) using leap-year calendar
cuml = np.array([0,31,60,91,121,152,182,213,244,274,305,335,366])
def doy_md(d):
    m = int(np.searchsorted(cuml, d, side='left')) - 1
    return m + 1, d - cuml[m]

# build pool day masks
masks = {}
for d in range(1, 367):
    if d == 60:
        continue
    mo, da = doy_md(d)
    mask = np.zeros(4028, bool)
    for y in range(1992, 2003):
        B = np.datetime64('%04d-%02d-%02d' % (y, mo, da))
        lo = int(B.astype('datetime64[D]').astype('int64')) - 5
        hi = lo + 10
        i0 = int(np.searchsorted(wd_int, lo, 'left'))
        i1 = int(np.searchsorted(wd_int, hi, 'right'))
        assert i1 - i0 == 11, (d, y, i0, i1)
        mask[i0:i1] = True
    assert mask.sum() == 121, (d, mask.sum())
    masks[d] = mask

union = np.zeros(4028, bool)
for m in masks.values(): union |= m
print('union of pools covers all 4028 window days:', bool(union.all()),
      '| pool size min/max:', min(m.sum() for m in masks.values()), max(m.sum() for m in masks.values()))

# 90th pct (hazen) threshold and mean climatology per DOY (skip 60)
thr  = np.empty((366, nsea)); clim = np.empty((366, nsea))
t0 = tm.time()
for d in range(1, 367):
    if d == 60:
        continue
    vals = winf[masks[d]]                            # (121, nsea), all finite for sea cells
    thr[d-1]  = np.quantile(vals, 0.9, axis=0, method='hazen')
    clim[d-1] = vals.mean(axis=0)
print('pools stats: %.1fs' % (tm.time() - t0))

# day 60 <- mean of day 59 and 61
thr[59]  = 0.5 * (thr[58] + thr[60])
clim[59] = 0.5 * (clim[58] + clim[60])

# centred 31-day moving mean, wrapping mod 366
def smooth31(A):
    ext = np.concatenate([A[-15:], A, A[:15]], axis=0)
    cs = np.vstack([np.zeros((1, A.shape[1])), np.cumsum(ext, axis=0)])
    return (cs[31:] - cs[:-31]) / 31.0

thr_s  = smooth31(thr)
clim_s = smooth31(clim)
np.save('/tmp/thr_sm.npy', thr_s); np.save('/tmp/clim_sm.npy', clim_s)
print('thr_s', thr_s.shape, 'finite:', bool(np.isfinite(thr_s).all()), bool(np.isfinite(clim_s).all()))
c = 0
print('sample cell0: raw thr DOY153-162 :', np.round(thr[152:162, c], 4))
print('sample cell0: sm  thr DOY153-162 :', np.round(thr_s[152:162, c], 4))
print('sample cell0: sm  clim DOY153-162:', np.round(clim_s[152:162, c], 4))
print('sample cell0: raw clim DOY59-62  :', np.round(clim[58:62, c], 4))
print('total elapsed %.1fs' % (tm.time() - t_start))
