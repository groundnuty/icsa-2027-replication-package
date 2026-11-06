import numpy as np, datetime as dt, time
import warnings; warnings.filterwarnings('ignore')
t_start = time.time()
S_base = np.load('/work/S_base.npy')
cr = np.load('/work/coords.npz')
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

thr = np.full((366, NC), np.nan); clim = np.full((366, NC), np.nan)
for d in range(1, 367):
    if d == 60: continue
    X = S_base[pool_mask[d]].reshape(-1, NC)
    thr[d-1] = np.nanquantile(X, 0.9, method='hazen', axis=0)
    clim[d-1] = np.nanmean(X, axis=0)
thr[59] = 0.5*(thr[58]+thr[60]); clim[59] = 0.5*(clim[58]+clim[60])
print("pools done", time.time()-t_start)

idx = (np.arange(366)[:, None] + (-15 + np.arange(31))[None, :]) % 366
thr_s = thr[idx].mean(axis=1); clim_s = clim[idx].mean(axis=1)
assert thr_s.shape == (366, NC)

# rigorous check of wrap smoothing vs explicit definition
rng = np.random.default_rng(0)
x = rng.standard_normal(366)
sm = x[idx].mean(axis=1)
ok = True
for i in range(366):
    w = [(i+j) % 366 for j in range(-15, 16)]
    if not np.isclose(sm[i], np.mean([x[j] for j in w])):
        ok = False; print("mismatch at", i); break
print("wrap smoothing verified:", ok)

sea_cells = np.where(np.isfinite(np.load('/work/S_tgt.npy')).all(axis=0))[0]
print("sea cells:", sea_cells.size, "all finite thr_s:", bool(np.all(np.isfinite(thr_s[:, sea_cells]))))

np.save('/work/thr_s.npy', thr_s); np.save('/work/clim_s.npy', clim_s)
np.save('/work/sea_cells.npy', sea_cells); np.save('/work/tgt_doy.npy', tgt_doy)
print("SAVED", time.time()-t_start)
