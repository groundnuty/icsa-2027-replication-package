import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print("----")
for v in ds.variables:
    print(v, ds[v].dtype)
print("----")
print("time:", ds.time.values[:5], ds.time.values[-5:])
print("lat range:", float(ds.lat.min()), float(ds.lat.max()))
print("lon range:", float(ds.lon.min()), float(ds.lon.max()))
print("lat n:", len(ds.lat), "lon n:", len(ds.lon), "time n:", len(ds.time))
