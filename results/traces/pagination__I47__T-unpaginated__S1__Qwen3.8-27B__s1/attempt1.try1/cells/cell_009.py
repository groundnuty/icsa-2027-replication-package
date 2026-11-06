
import fsspec, xarray as xr, time
fs = fsspec.filesystem('onedata')
t0 = time.time()
f = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_20190601.nc', 'rb')
ds = xr.open_dataset(f, engine="h5netcdf")
v = ds['analysed_sst']
print("var attrs:", dict(v.attrs))
lat = ds['latitude'].values; lon = ds['longitude'].values
print("lat dtype", lat.dtype, "lon dtype", lon.dtype)
import numpy as np
il = np.where((lat >= 64.39) & (lat <= 65.59))[0]
ij = np.where((lon >= 23.41) & (lon <= 24.61))[0]
print("lat idx:", il[0], il[-1], "count", len(il), "values:", lat[il[0]], lat[il[-1]])
print("lon idx:", ij[0], ij[-1], "count", len(ij), "values:", lon[ij[0]], lon[ij[-1]])
sub = v.values[:, il[0]:il[-1]+1, ij[0]:ij[-1]+1]
print("sub shape", sub.shape, "finite all:", np.isfinite(sub).all(), "min/max:", np.nanmin(sub), np.nanmax(sub))
# full grid finite count for this day
print("full finite:", np.isfinite(v.values).sum(), "of", v.values.size)
ds.close(); f.close()
print("time for one file open+read:", time.time()-t0, "s")
