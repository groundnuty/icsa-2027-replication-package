import numpy as np
import pandas as pd
import xarray as xr

z = np.load('/work/intermediate.npz')
thr, clim = z['thr'], z['clim']
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t_all = ds.time.values
u0 = np.searchsorted(t_all, np.datetime64('2022-06-01')); u1 = np.searchsorted(t_all, np.datetime64('2022-08-31'))
S_tgt = ds.analysed_sst.isel(time=slice(u0,u1+1), latitude=slice(66,126), longitude=slice(531,591)).values.astype(np.float64)
fin = np.isfinite(S_tgt).all(axis=0)

b0 = np.searchsorted(t_all, np.datetime64('1991-12-27'))
t_ext = t_all[b0:b0+4028]
tt = pd.to_datetime(t_ext)
doy_ext = (pd.to_datetime(dict(year=2020, month=tt.month, day=tt.day)) - pd.Timestamp('2020-01-01')).dt.days + 1
doy_ext = doy_ext.to_numpy()
in_base = (t_ext >= np.datetime64('1992-01-01')) & (t_ext <= np.datetime64('2002-12-31'))
base_idx = np.flatnonzero(in_base); doy_base = doy_ext[base_idx]
bi = base_idx[doy_base == 153]
offs = np.unique(np.concatenate([np.arange(k-5, k+6) for k in bi]))
S_ext = ds.analysed_sst.isel(time=slice(b0,b0+4028), latitude=slice(66,126), longitude=slice(531,591)).values.astype(np.float64)
ds.close()

# cross-check several DOYs and several sea cells
sea_idx = np.flatnonzero(fin.ravel())
rng = np.random.default_rng(0)
ok_q = ok_m = True
for d in [1, 61, 153, 244, 366]:
    bi = base_idx[doy_base == d]
    offs = np.unique(np.concatenate([np.arange(k-5, k+6) for k in bi]))
    for c in rng.choice(sea_idx, 5, replace=False):
        r, cc = divmod(int(c), 60)
        pool = S_ext[offs, r, cc].ravel()
        v = pool[np.isfinite(pool)]
        n = len(v); h = n*0.9 + 0.5
        lo = int(np.floor(h)) - 1; frac = h - np.floor(h)
        sv = np.sort(v)
        manual = sv[lo] + frac*(sv[min(lo+1, n-1)] - sv[lo])
        ok_q &= np.isclose(manual, thr[d-1, c], rtol=1e-12)
        ok_m &= np.isclose(v.mean(), clim[d-1, c], rtol=1e-12)
print("hazen quantile matches manual (25 checks):", ok_q)
print("climatology mean matches (25 checks):", ok_m)

# day-60 rule check: use smoothed? No - pre-smoothing:
print("day60 = mean(59,61) pre-smoothing:",
      np.allclose(thr[59], 0.5*(thr[58]+thr[60])), np.allclose(clim[59], 0.5*(clim[58]+clim[60])))

# smoothing check on a synthetic array
def circ31(a):
    ext = np.concatenate([a[-15:], a, a[:15]], axis=0)
    w = np.lib.stride_tricks.sliding_window_view(ext, 31, axis=0)
    return w.mean(axis=-1)
a = np.arange(366, dtype=float)
s = circ31(a)
# day 1 (index 0): mean of idx -15..15 mod 366 = 351..365, 0..15
m = np.mean(list(a[351:366]) + list(a[0:16]))
print("smooth day1:", s[0], "manual:", m, np.isclose(s[0], m))
# day 366 (index 365): idx 350..365, 0..14
m = np.mean(list(a[350:366]) + list(a[0:15]))
print("smooth day366:", s[365], "manual:", m, np.isclose(s[365], m))
# interior day: index 100 -> 85..115
m = np.mean(a[85:116])
print("smooth day101:", s[100], "manual:", m, np.isclose(s[100], m))

# smoothed threshold summer stats (finite cells)
thr_s = z['thr_s']
mask_f = np.isfinite(thr_s[152:245, :]).all(axis=0)
print("mean smoothed thr Jun-Aug (K):", round(float(thr_s[152:245, mask_f].mean()), 3),
      "min:", round(float(np.nanmin(thr_s[152:245, mask_f])), 3),
      "max:", round(float(np.nanmax(thr_s[152:245, mask_f])), 3))
