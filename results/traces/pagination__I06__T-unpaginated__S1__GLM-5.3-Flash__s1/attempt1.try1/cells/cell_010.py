import numpy as np, datetime as dt, pickle, time

base_sst = np.load('/tmp/base_sst.npy')
with open('/tmp/meta.pkl','rb') as f:
    meta = pickle.load(f)
base_dates = [dt.date.fromisoformat(s) for s in meta['base_dates']]

def doy366(d):
    if d.month == 2 and d.day == 29:
        return 60
    if d.month <= 2:
        return (d - dt.date(d.year,1,1)).days + 1
    return 61 + (d - dt.date(d.year,3,1)).days

B0, B1 = dt.date(1992,1,1), dt.date(2002,12,31)
pool_idx = {}
for xi, X in enumerate(base_dates):
    for off in range(-5, 6):
        B = X + dt.timedelta(days=off)
        if B0 <= B <= B1:
            d = doy366(B)
            if d != 60:
                pool_idx.setdefault(d, []).append(xi)

bs64 = base_sst.astype(np.float64)
t0=time.time()
thr_raw = np.full((366, 60, 60), np.nan)
clim_raw = np.full((366, 60, 60), np.nan)
for d in range(1, 367):
    idx = pool_idx[d]
    block = bs64[idx]                       # (121, 60, 60) float64
    thr_raw[d] = np.nanpercentile(block, 90, axis=0, method='hazen')
    clim_raw[d] = np.nanmean(block, axis=0)
print("pool stats sec:", time.time()-t0)

# day 60 = mean of days 59 and 61
thr_raw[60] = 0.5*(thr_raw[59] + thr_raw[61])
clim_raw[60] = 0.5*(clim_raw[59] + clim_raw[61])
print("day60 finite:", np.isfinite(thr_raw[1:]).all(), np.isfinite(clim_raw[1:]).all())

# circular centred 31-day moving mean
def circ_movmean31(a):
    ap = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.cumsum(ap, axis=0)
    out = (c[30:] - c[:-30]) / 31.0
    return out[:366] if out.shape[0]==366 else out
# careful: c[30:]-c[:-30] gives len 366 (376-... let's just verify shapes)
ap = np.concatenate([thr_raw[-15:], thr_raw, thr_raw[:15]], axis=0)
print("padded len:", ap.shape)
c = np.cumsum(ap, axis=0)
mov = (c[30:] - c[:-30]) / 31.0
print("mov shape:", mov.shape)
thr = mov.copy()
ap2 = np.concatenate([clim_raw[-15:], clim_raw, clim_raw[:15]], axis=0)
c2 = np.cumsum(ap2, axis=0)
clim = (c2[30:] - c2[:-30]) / 31.0
print("thr finite:", np.isfinite(thr).all(), "clim finite:", np.isfinite(clim).all())

# independent check of the moving mean via direct modulo sum for a few days
for d in [1, 60, 153, 244, 366]:
    ds = [(d + k - 1) % 366 + 1 for k in range(-15, 16)]
    m = thr_raw[ds].mean(axis=0)
    assert np.allclose(m, thr[d]), d
print("circular moving mean verified against direct modulo sums")

# verify day-60 fill inside smoothed arrays is consistent (it's a linear op, but check day 60 equals mean of 59,61 pre-smoothing was applied -> smoothing mixes anyway; just sanity range)
print("thr sample (cell 30,30) doy 153-160:", np.round(thr[153:161, 30, 30], 3))
print("clim sample (cell 30,30) doy 153-160:", np.round(clim[153:160, 30, 30], 3))
print("thr range:", np.nanmin(thr), np.nanmax(thr), " clim range:", np.nanmin(clim), np.nanmax(clim))

np.save('/tmp/thr.npy', thr)
np.save('/tmp/clim.npy', clim)
print("saved thr, clim")
