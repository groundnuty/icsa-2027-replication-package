import numpy as np, datetime as dt
cr = np.load('/work/coords.npz')
# reload what we saved? We crashed before saving thr_s... recompute quickly is 5 min.
# Actually the crash happened AFTER "smoothed ok" but before np.save. Ugh. Recompute pools from saved S arrays.

S_base = np.load('/work/S_base.npy')
S_tgt  = np.load('/work/S_tgt.npy')
lat, lon = cr['lat'], cr['lon']
base_dates = [dt.date.fromisoformat(str(d)) for d in cr['baseline_dates'].astype('datetime64[D]').astype(object)]
tgt_dates  = [dt.date.fromisoformat(str(d)) for d in cr['target_dates'].astype('datetime64[D]').astype(object)]
nd, nlat, nlon = S_base.shape
NC = nlat*nlon

def doy(d):
    cum=[0]
    for L in [31,29,31,30,31,30,31,31,30,31,30,31]: cum.append(cum[-1]+L)
    return cum[d.month-1]+d.day
base_doy = np.array([doy(d) for d in base_dates])
tgt_doy  = np.array([doy(d) for d in tgt_dates])
sea_cells = np.where(np.isfinite(S_tgt).all(axis=0))[0]

date_to_idx = {d: i for i, d in enumerate(base_dates)}
b_idx_by_doy = {}
for i, d in enumerate(base_dates):
    if dt.date(1992,1,1) <= d <= dt.date(2002,12,31):
        b_idx_by_doy.setdefault(base_doy[i], []).append(i)

pool_mask = np.zeros((367, nd), dtype=bool)
for d in range(1, 367):
    if d == 60: continue
    for bi in b_idx_by_doy[d]:
        b = base_dates[bi]
        for k in range(-5, 6):
            pool_mask[d, date_to_idx[b + dt.timedelta(days=k)]] = True

thr = np.full((366, NC), np.nan); clim = np.full((366, NC), np.nan)
for d in range(1, 367):
    if d == 60: continue
    X = S_base[pool_mask[d]].reshape(-1, NC)
    thr[d-1] = np.nanquantile(X, 0.9, method='hazen', axis=0)
    clim[d-1] = np.nanmean(X, axis=0)
thr[59] = 0.5*(thr[58]+thr[60]); clim[59] = 0.5*(clim[58]+clim[60])

def smooth31(x):
    padded = np.tile(x, 3)[15:15+366]
    return np.lib.stride_tricks.sliding_window_view(padded, 31, axis=0).mean(axis=1)
thr_s = smooth31(thr); clim_s = smooth31(clim)

bad = ~np.isfinite(thr_s).any(axis=0)   # cells with NO NaN: shape (NC,)
bad_cells = np.where(bad)[0]
sea_set = set(sea_cells.tolist())
land_bad = [c for c in bad_cells if c not in sea_set]
sea_bad  = [c for c in bad_cells if c in sea_set]
print("clean cells:", len(bad_cells), " land-clean:", len(land_bad), " sea-clean:", len(sea_bad))
# any sea cell NaN on target doys?
td = list(set(tgt_doy.tolist()))
sea_nan_tgt = [c for c in sea_cells if (~np.isfinite(thr_s[td, c])).any()]
print("sea cells with NaN thr on any target doy:", len(sea_nan_tgt), sea_nan_tgt[:10])

np.save('/work/thr_s.npy', thr_s); np.save('/work/clim_s.npy', clim_s)
np.save('/work/sea_cells.npy', sea_cells); np.save('/work/tgt_doy.npy', tgt_doy)
print("SAVED")
