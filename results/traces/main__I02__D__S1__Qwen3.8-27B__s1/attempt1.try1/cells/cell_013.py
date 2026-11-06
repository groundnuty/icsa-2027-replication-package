import numpy as np, datetime as dt, time

t_start = time.time()
S_base = np.load('/work/S_base.npy')
S_tgt  = np.load('/work/S_tgt.npy')
cr = np.load('/work/coords.npz')
lat, lon = cr['lat'], cr['lon']
base_dates = [dt.date.fromisoformat(str(d)) for d in cr['baseline_dates'].astype('datetime64[D]').astype(object)]
tgt_dates  = [dt.date.fromisoformat(str(d)) for d in cr['target_dates'].astype('datetime64[D]').astype(object)]
nd, nlat, nlon = S_base.shape
NC = nlat*nlon

def doy(d):
    cum = [0]
    for L in [31,29,31,30,31,30,31,31,30,31,30,31]:
        cum.append(cum[-1]+L)
    return cum[d.month-1] + d.day

base_doy = np.array([doy(d) for d in base_dates])
tgt_doy  = np.array([doy(d) for d in tgt_dates])
sea_cells = np.where(np.isfinite(S_tgt).all(axis=0))[0]
print("sea cells:", sea_cells.size, "of", NC)

date_to_idx = {d: i for i, d in enumerate(base_dates)}
b_idx_by_doy = {}
for i, d in enumerate(base_dates):
    if dt.date(1992,1,1) <= d <= dt.date(2002,12,31):
        b_idx_by_doy.setdefault(base_doy[i], []).append(i)
assert set(b_idx_by_doy) == set(range(1,367))
for d, lst in b_idx_by_doy.items():
    assert (d == 60 and len(lst) == 3) or (d != 60 and len(lst) == 11), (d, len(lst))

pool_mask = np.zeros((367, nd), dtype=bool)
ps = []
for d in range(1, 367):
    if d == 60: continue
    for bi in b_idx_by_doy[d]:
        b = base_dates[bi]
        for k in range(-5, 6):
            pool_mask[d, date_to_idx[b + dt.timedelta(days=k)]] = True
    ps.append(int(pool_mask[d].sum()))
ps = np.array(ps)
print("pool size min/max:", ps.min(), ps.max())

thr = np.full((366, NC), np.nan)
clim = np.full((366, NC), np.nan)
for d in range(1, 367):
    if d == 60: continue
    X = S_base[pool_mask[d]].reshape(-1, NC)
    thr[d-1] = np.nanquantile(X, 0.9, method='hazen', axis=0)
    clim[d-1] = np.nanmean(X, axis=0)
print("pools done", time.time()-t_start)

thr[59] = 0.5*(thr[58]+thr[60]); clim[59] = 0.5*(clim[58]+clim[60])  # 0-based: day60=idx59, day59=idx58, day61=idx60

def smooth31(x):
    padded = np.tile(x, 3)[15:15+366]
    return np.lib.stride_tricks.sliding_window_view(padded, 31).mean(axis=1)
thr_s = smooth31(thr); clim_s = smooth31(clim)
print("smoothed ok; thr_s all finite:", bool(np.isfinite(thr_s).all()))
print("thr_s range:", thr_s.min(), thr_s.max())

np.save('/work/thr_s.npy', thr_s); np.save('/work/clim_s.npy', clim_s)
np.save('/work/sea_cells.npy', sea_cells); np.save('/work/tgt_doy.npy', tgt_doy)
print("CORE DONE", time.time()-t_start)
