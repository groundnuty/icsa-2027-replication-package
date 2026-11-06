import fsspec, xarray as xr, numpy as np

fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = fs.open(path, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
lat = ds.latitude.values; lon = ds.longitude.values
print("lat dtype:", lat.dtype, "first/last:", lat[0], lat[-1], "n:", lat.size)
print("lon dtype:", lon.dtype, "first/last:", lon[0], lon[-1], "n:", lon.size)
# exact float32 values near bounds
for b in (57.57, 58.77):
    idx = np.where(np.abs(lat.astype('float64')-b) < 0.05)[0]
    print(b, "nearby lat:", lat[idx].astype('float64'))
for b in (10.25, 11.45):
    idx = np.where(np.abs(lon.astype('float64')-b) < 0.05)[0]
    print(b, "nearby lon:", lon[idx].astype('float64'))
# step sizes
print("lat diffs unique:", np.unique(np.diff(lat.astype('float64')))[:5])
print("lon diffs unique:", np.unique(np.diff(lon.astype('float64')))[:5])
t = ds.time.values
print("time:", t[0], t[-1], t.size)
d = np.diff(t).astype('timedelta64[D]')
print("time diffs unique:", np.unique(d))
print("sst encoding:", ds.analysed_sst.encoding)
print("sst attrs:", ds.analysed_sst.attrs)
