import numpy as np, datetime as dt, time
import warnings; warnings.filterwarnings('ignore')
t_start = time.time()
S_base = np.load('/work/S_base.npy'); S_tgt = np.load('/work/S_tgt.npy')
cr = np.load('/work/coords.npz'); lat, lon = cr['lat'], cr['lon']
base_dates = [dt.date.fromisoformat(str(d)) for d in cr['baseline_dates'].astype('datetime64[D]').astype(object)]
tgt_dates  = [dt.date.fromisoformat(str(d)) for d in cr['target_dates'].astype('datetime64[D]').astype(object)]
nd, nlat, nlon = S_base.shape
NC = nlat*nlon
print("S_base", S_base.shape, "NC", NC)

def doy(d):
    cum=[0]
    for L in [31,29,31,30,31,30,31,31,30,31,30,31]: cum.append(cum[-1]+L)
    return cum[d.month-1]+d.day
base_doy = np.array([doy(d) for d in base_dates])
tgt_doy  = np.array([doy(d) for d in tgt_dates])
sea_cells = np.where(np.isfinite(S_tgt).all(axis=0))[0]
print("sea cells:", sea_cells.size)

date_to_idx = {d: i for i, d in enumerate(base_dates)}
b_idx_by_doy = {}
for i, d in enumerate(base_dates):
    if dt.date(1992,1,1) <= d <= dt.date(2002,12,31):
        b_idx_by_doy.setdefault(base_doy[i], []).append(i)
assert set(b_idx_by_doy) == set(range(1,367))

pool_mask = np.zeros((367, nd), dtype=bool)
for d in range(1, 367):
    if d == 60: continue
    for bi in b_idx_by_doy[d]:
        b = base_dates[bi]
        for k in range(-5, 6):
            pool_mask[d, date_to_idx[b + dt.timedelta(days=k)]] = True
print("pool_mask", pool_mask.shape)

thr = np.full((366, NC), np.nan); clim = np.full((366, NC), np.nan)
for d in range(1, 367):
    if d == 60: continue
    X = S_base[pool_mask[d]].reshape(-1, NC)
    thr[d-1] = np.nanquantile(X, 0.9, method='hazen', axis=0)
    clim[d-1] = np.nanmean(X, axis=0)
print("pools done", time.time()-t_start, "thr", thr.shape)
thr[59] = 0.5*(thr[58]+thr[60]); clim[59] = 0.5*(clim[58]+clim[60])

# NaN audit BEFORE smoothing
nanpre = ~np.isfinite(thr)
print("cells with all-NaN thr (pre-smooth):", int((~nanpre.any(axis=0)).sum()),
      "| cells with some NaN:", int(nanpre.any(axis=0).sum()))
sea_set = set(sea_cells.tolist())
sea_allnan = [c for c in np.where(~nanpre.any(axis=0))[0] if c in sea_set]
print("SEA cells with all-NaN thr pre-smooth:", len(sea_allnan), sea_allnan[:20])

# correct wrap-around centred 31-day moving mean
idx = (np.arange(366)[:, None] + (-15 + np.arange(31))[None, :]) % 366   # (366, 31)
thr_s = thr[idx].mean(axis=1); clim_s = clim[idx].mean(axis=1)
print("thr_s", thr_s.shape, "clim_s", clim_s.shape)
# sanity checks
assert thr_s.shape == (366, NC)
x = np.zeros(366); 
idx1 = (np.arange(366)[:, None] + (-15 + np.arange(31))[None, :]) % 366
assert np.allclose(x[idx1].mean(axis=1), 0.0)
x = np.arange(366, dtype=float)
sm = x[idx1].mean(axis=1)
# day i (0-based) averages i-15..i+15 mod 366; check i=0 -> 351..365,0..15
manual = (np.r_[x[351:366], x[0:16]]).mean()
print("sm[0]:", sm[0], "manual:", manual, "match:", np.isclose(sm[0], manual))
x2 = np.arange(366, dtype=float); 
manual2 = x2[(365-15)%366:(365-15)%366+31].mean()  # linear window for i=365 no wrap
assert np.isclose(sm[365], manual2)
print("smoothing verified")

nanpost = ~np.isfinite(thr_s)
print("post-smooth: sea cells with any NaN thr:", int(sum(1 for c in sea_cells if nanpost[:, c].any())))
td = list(set(tgt_doy.tolist()))
sea_nan_tgt = [c for c in sea_cells if nanpost[td, c].any()]
print("sea cells with NaN thr on TARGET doys:", len(sea_nan_tgt), sea_nan_tgt[:20])

np.save('/work/thr_s.npy', thr_s); np.save('/work/clim_s.npy', clim_s)
np.save('/work/sea_cells.npy', sea_cells); np.save('/work/tgt_doy.npy', tgt_doy)
print("SAVED, total", time.time()-t_start)
