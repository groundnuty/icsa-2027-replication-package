import numpy as np
import pandas as pd

z = np.load('/work/intermediate.npz')
thr, clim, thr_s, clim_s = z['thr'], z['clim'], z['thr_s'], z['clim_s']
doy_tgt = z['doy_tgt']; lat, lon = z['lat'], z['lon']; t_tgt = z['t_tgt']
NC = 3600

# 1) pool sizes: recompute for each DOY and check sizes
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t_all = ds.time.values
b0 = np.searchsorted(t_all, np.datetime64('1991-12-27'))
t_ext = t_all[b0:b0+4028]
def doy_of(t64):
    tt = pd.to_datetime(t64)
    ref = pd.to_datetime(dict(year=2020, month=tt.month.to_numpy(), day=tt.day.to_numpy())) - pd.Timestamp('2020-01-01')
    return ref.dt.days.to_numpy() + 1
doy_ext = doy_of(t_ext)
in_base = (t_ext >= np.datetime64('1992-01-01')) & (t_ext <= np.datetime64('2002-12-31'))
base_idx = np.flatnonzero(in_base); doy_base = doy_ext[base_idx]

sizes = {}
for d in [1, 59, 60, 61, 153, 366]:
    bi = base_idx[doy_base == d]
    offs = np.unique(np.concatenate([np.arange(k-5, k+6) for k in bi]))
    sizes[d] = len(offs)
    print(f"DOY {d}: n baseline dates={len(bi)}, pool days={len(offs)}, "
          f"first pool date={t_ext[offs[0]].astype('datetime64[D]')}, last={t_ext[offs[-1]].astype('datetime64[D]')}")
# all pool sizes distinct?
all_ok = all(len(np.unique(np.concatenate([np.arange(k-5,k+6) for k in base_idx[doy_base==d]])))==121
             for d in range(1,367) if d!=60)
print("all non-60 DOY pools have exactly 121 days:", all_ok)

# 2) manual hazen quantile cross-check on DOY 153 for one cell
c = 100
bi = base_idx[doy_base == 153]
offs = np.unique(np.concatenate([np.arange(k-5, k+6) for k in bi]))
S_ext = ds.analysed_sst.isel(time=slice(b0, b0+4028),
                             latitude=slice(66,126), longitude=slice(531,591)).values.astype(np.float64)
ds.close()
pool = S_ext[offs, 1, 3].ravel()  # some cell (lat idx 1 within region, lon idx 3)
v = pool[np.isfinite(pool)]
n = len(v); h = n*0.9 + 0.5  # hazen 1-indexed
lo = int(np.floor(h)) - 1; frac = h - np.floor(h)
sv = np.sort(v)
manual = sv[lo] + frac*(sv[min(lo+1,n-1)] - sv[lo])
print(f"DOY153 cell(1,3): pool n={n}, manual hazen q90={manual!r}, numpy thr[152]={thr[152,c]!r}")
print("match:", np.isclose(manual, thr[152, c], rtol=1e-12))
print("clim manual vs numpy:", np.isclose(v.mean(), clim[152, c]))

# 3) sanity: summer thresholds (K)
sm = thr_s[152:245, :].mean(axis=1)
print("mean smoothed threshold over Jun-Aug days (K):", sm.min(), sm.max())
print("target SST range (K):", np.nanmin(z['M'] and None or 0) if False else "")
