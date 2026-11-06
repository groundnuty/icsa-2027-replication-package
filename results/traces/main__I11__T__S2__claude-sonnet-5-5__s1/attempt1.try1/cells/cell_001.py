import fsspec,xarray as xr
fs=fsspec.filesystem('onedata')
f=fs.open("icsa2027_data_20261101T090944Z/s2z/sst_s2.nc","rb")
ds=xr.open_dataset(f,engine="h5netcdf")
print(ds)
t=ds.time.values;print(t[:2],t[-2:],len(t))