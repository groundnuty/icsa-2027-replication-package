import fsspec, xarray as xr, numpy as np, time, pandas as pd
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat = ds.latitude.values; lon = ds.longitude.values; t = ds.time.values
eps = 1e-6
li = np.where((lat >= 54.17 - eps) & (lat <= 55.37 + eps))[0]
lo = np.where((lon >= 13.25 - eps) & (lon <= 14.45 + eps))[0]
def idx(ts): return int(np.searchsorted(t, np.datetime64(ts)))
i0, i1 = idx('1991-12-27'), idx('2003-01-05')
j0, j1 = idx('2004-06-01'), idx('2004-08-31')
print("ext baseline idx:", i0, i1, "n days:", i1-i0+1, t[i0], t[i1])
print("target idx:", j0, j1, "n days:", j1-j0+1, t[j0], t[j1])
# timing: 10-day block over region
t_start = time.time()
blk = ds['analysed_sst'].isel(time=slice(0,10), latitude=slice(int(li[0]), int(li[-1])+1), longitude=slice(int(lo[0]), int(lo[-1])+1)).values
el = time.time()-t_start
print(f"10-day block: {el:.2f}s, shape {blk.shape}, dtype {blk.dtype}, finite frac {np.isfinite(blk).mean():.4f}")
# timing: 40-day block to estimate rate
t_start = time.time()
blk2 = ds['analysed_sst'].isel(time=slice(i0, i0+40), latitude=slice(int(li[0]), int(li[-1])+1), longitude=slice(int(lo[0]), int(lo[-1])+1)).values
el2 = time.time()-t_start
print(f"40-day block: {el2:.2f}s, shape {blk2.shape}, finite frac {np.isfinite(blk2).mean():.4f}")
