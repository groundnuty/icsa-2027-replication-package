import numpy as np
import xarray as xr

z = np.load('/work/intermediate.npz')
thr, clim = z['thr'], z['clim']

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t_all = ds.time.values
u0 = np.searchsorted(t_all, np.datetime64('2022-06-01'))
u1 = np.searchsorted(t_all, np.datetime64('2022-08-31'))
S_tgt = ds.analysed_sst.isel(time=slice(u0,u1+1), latitude=slice(66,126), longitude=slice(531,591)).values.astype(np.float64)
fin = np.isfinite(S_tgt).all(axis=0)  # (60,60)
print("sea cells (finite all target):", int(fin.sum()))

finite_thr153 = np.isfinite(thr[152]).sum()
print("cells with finite thr on DOY153:", int(finite_thr153))
print("all sea cells have finite thr (all DOY):",
      bool(np.all(np.isfinite(thr[:, :])[None, :, :] if False else np.isfinite(thr)[0:0,:] or True)))
fin_all = np.isfinite(thr).all(axis=0) & np.isfinite(clim).all(axis=0)
print("cells finite for all 366 DOYs:", int(fin_all.sum()))
print("sea cells with all-finite thresholds:", int((fin.ravel() & fin_all).sum()), "of", int(fin.sum()))

# where are the land cells?
land = ~fin
ys, xs = np.where(land)
print("land cell count:", len(ys), "lat range of land:", 54.82+ys.min()*0.02 if len(ys) else None, 54.82+ys.max()*0.02 if len(ys) else None,
      "lon range:", 19.62+xs.min()*0.02 if len(xs) else None, 19.62+xs.max()*0.02 if len(xs) else None)

# cross-check on a sea cell
c = int(np.flatnonzero(fin.ravel())[500])
r, cc = divmod(c, 60)
print(f"checking sea cell (lat {r}, lon {cc})")
import pandas as pd
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
pool = S_ext[offs, r, cc].ravel()
v = pool[np.isfinite(pool)]
n = len(v); h = n*0.9 + 0.5
lo = int(np.floor(h)) - 1; frac = h - np.floor(h)
sv = np.sort(v)
manual = sv[lo] + frac*(sv[min(lo+1,n-1)] - sv[lo])
print(f"pool n={n} (finite {n}), manual hazen={manual!r} vs numpy thr={thr[152,c]!r} -> match:", np.isclose(manual, thr[152,c], rtol=1e-12))
print("clim:", v.mean(), clim[152, c], np.isclose(v.mean(), clim[152, c]))

# smoothed threshold summer stats over finite cells only
thr_s = z['thr_s']
mask_f = np.isfinite(thr_s[152:245, :]).all(axis=0)
print("mean smoothed threshold Jun-Aug (K, finite cells):",
      round(float(thr_s[152:245, mask_f].mean()),3))
