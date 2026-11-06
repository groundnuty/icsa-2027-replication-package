import fsspec, xarray as xr, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
t0=time.time()
f = fs.open(f"{base}/sst_20210601.nc", "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
print("open+load hdr:", time.time()-t0, "s")
print(ds)
print("---")
for c in ds.coords:
    v = ds[c].values
    print(c, ds[c].dtype, ds[c].shape, v.ravel()[:6] if v.size else v)
