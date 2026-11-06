import numpy as np, datetime as dt, pickle, time, warnings

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
thr_raw = np.full((367, 60, 60), np.nan)   # day d at index d; index 0 unused
clim_raw = np.full((367, 60, 60), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60:
            continue
        block = bs64[pool_idx[d]]
        thr_raw[d] = np.nanpercentile(block, 90, axis=0, method='hazen')
        clim_raw[d] = np.nanmean(block, axis=0)
print("pool stats sec:", round(time.time()-t0,1))

thr_raw[60] = 0.5*(thr_raw[59] + thr_raw[61])
clim_raw[60] = 0.5*(clim_raw[59] + clim_raw[61])
print("day60 filled; all finite:", np.isfinite(thr_raw[1:]).all(), np.isfinite(clim_raw[1:]).all())

t366 = thr_raw[1:]     # entry j = day j+1
c366 = clim_raw[1:]

def circ_movmean31(a):
    ap = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.cumsum(ap, axis=0)
    return (c[30:] - c[:-30]) / 31.0

thr = circ_movmean31(t366)    # entry j = smoothed day j+1
clim = circ_movmean31(c366)
print("shapes:", thr.shape, clim.shape)

# verification vs direct modulo sums (0-based index into t366 = day-1)
for d in [1, 2, 60, 61, 153, 244, 365, 366]:
    idxs = [(d - 1 + k) % 366 for k in range(-15, 16)]
    assert np.allclose(t366[idxs].mean(axis=0), thr[d-1], atol=1e-12), d
    assert np.allclose(c366[idxs].mean(axis=0), clim[d-1], atol=1e-12), d
print("circular moving mean verified for days 1,2,60,61,153,244,365,366")

alt = sum(np.roll(t366, -k, axis=0) for k in range(-15, 16)) / 31.0
print("roll-based check max abs diff:", np.abs(alt - thr).max())
alt2 = sum(np.roll(c366, -k, axis=0) for k in range(-15, 16)) / 31.0
print("roll-based check clim max abs diff:", np.abs(alt2 - clim).max())

print("thr (cell 30,30): doy152-156:", np.round(thr[151:156, 30, 30], 4))
print("clim (cell 30,30): doy152-156:", np.round(clim[151:156, 30, 30], 4))
print("thr range:", thr.min(), thr.max(), "clim range:", clim.min(), clim.max())

np.save('/tmp/thr.npy', thr)      # entry j = day j+1
np.save('/tmp/clim.npy', clim)
with open('/tmp/pools.pkl','wb') as f:
    pickle.dump({str(k): v for k,v in pool_idx.items()}, f)
print("saved thr, clim, pools")
