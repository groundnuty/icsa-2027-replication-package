import xarray as xr
ds=xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc",engine="h5netcdf")
print(ds)
for v in ds.variables: print(v,ds[v].attrs, ds[v].encoding.get('dtype'))