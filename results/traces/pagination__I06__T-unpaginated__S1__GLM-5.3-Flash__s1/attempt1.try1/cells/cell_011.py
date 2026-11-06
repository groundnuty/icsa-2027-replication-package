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
thr_raw = np.full((366, 60, 60), np.nan)
clim_raw = np.full((366, 60, 60), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60:
            continue
        idx = pool_idx[d]
        block = bs64[idx]
        thr_raw[d] = np.nanpercentile(block, 90, axis=0, method='hazen')
        clim_raw[d] = np.nanmean(block, axis=0)
print("pool stats sec:", time.time()-t0)

thr_raw[60] = 0.5*(thr_raw[59] + thr_raw[61])
clim_raw[60] = 0.5*(clim_raw[59] + clim_raw[61])
print("day60 filled, finite all:", np.isfinite(thr_raw).all(), np.isfinite(clim_raw).all())

def circ_movmean31(a):   # a: (366, ...) -> centred 31-day circular moving mean
    ap = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.cumsum(ap, axis=0)
    return (c[30:] - c[:-30]) / 31.0

thr = circ_movmean31(thr_raw)
clim = circ_movmean31(clim_raw)
print("mov shapes:", thr.shape, clim.shape)

for d in [1, 60, 153, 244, 366]:
    ds = [(d + k - 1) % 366 + 1 for k in range(-15, 16)]
    assert np.allclose(thr_raw[ds].mean(axis=0), thr[d], atol=1e-12), d
    assert np.allclose(clim_raw[ds].mean(axis=0), clim[d], atol=1e-12), d
print("circular moving mean verified against direct modulo sums")

# alternate verification of cumsum trick with np.roll-based sum
alt = sum(np.roll(thr_raw, -k, axis=0) for k in range(-15, 16)) / 31.0
print("roll-based check max abs diff:", np.abs(alt - thr).max())

print("thr sample (cell 30,30) doy 153,154:", np.round(thr[[153,154], 30, 30], 4))
print("clim sample (cell 30,30) doy 153,154:", np.round(clim[[153,154], 30, 30], 4))
print("thr range:", thr.min(), thr.max(), " clim range:", clim.min(), clim.max())

np.save('/tmp/thr.npy', thr)
np.save('/tmp/clim.npy', clim)
print("saved")
