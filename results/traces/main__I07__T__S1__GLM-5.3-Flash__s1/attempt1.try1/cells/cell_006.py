import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
f = fs.open(f"{base}/sst_19920101.nc", "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
# check grid identical across files?
f2 = fs.open(f"{base}/sst_20210831.nc", "rb")
ds2 = xr.open_dataset(f2, engine="h5netcdf")
print("lat equal:", np.array_equal(ds.latitude.values, ds2.latitude.values))
print("lon equal:", np.array_equal(ds.longitude.values, ds2.longitude.values))
print("encoding:", ds.analysed_sst.encoding)
print("attrs:", ds.analysed_sst.attrs)
# region slice
lat = ds.latitude.values.astype('float64'); lon = ds.longitude.values.astype('float64')
print("lat range:", lat.min(), lat.max(), "step:", np.diff(lat)[:3], np.unique(np.round(np.diff(lat),6)))
print("lon range:", lon.min(), lon.max(), "step:", np.diff(lon)[:3])
