import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
v = ds['analysed_sst']
print("attrs:", dict(v.attrs))
print("encoding:", v.encoding)
lat = ds.latitude.values; lon = ds.longitude.values; t = ds.time.values
print("lat dtype", lat.dtype, "lon dtype", lon.dtype)
print("unique lat diffs:", np.unique(np.diff(lat)), "unique lon diffs:", np.unique(np.diff(lon)))
# region selection with tolerance
eps = 1e-6
li = np.where((lat >= 54.17 - eps) & (lat <= 55.37 + eps))[0]
lo = np.where((lon >= 13.25 - eps) & (lon <= 14.45 + eps))[0]
print("lat sel:", lat[li[0]], lat[li[-1]], len(li))
print("lon sel:", lon[lo[0]], lon[lo[-1]], len(lo))
print("lat values:", lat[li].astype(float))
print("lon values:", lon[lo].astype(float))
# date to index
ti = {d: i for i, d in enumerate(t)}
def idx(d): return int(np.searchsorted(t, d))
import pandas as pd
t0 = pd.Timestamp('1991-12-27'); t1 = pd.Timestamp('2003-01-05')
i0 = idx(t0); i1 = idx(t1)
print("ext baseline idx:", i0, i1, "n days:", i1-i0+1, t[i0], t[i1])
s0 = pd.Timestamp('2004-06-01'); s1 = pd.Timestamp('2004-08-31')
j0 = idx(s0); j1 = idx(s1)
print("target idx:", j0, j1, "n days:", j1-j0+1, t[j0], t[j1])
# timing a small read: 10 days x region block
t_start = time.time()
blk = ds['analysed_sst'].isel(time=slice(0,10), latitude=slice(int(li[0]), int(li[-1])+1), longitude=slice(int(lo[0]), int(lo[-1])+1)).values
print("10-day block read+values:", time.time()-t_start, "s", blk.shape, blk.dtype, "finite frac:", np.isfinite(blk).mean())
