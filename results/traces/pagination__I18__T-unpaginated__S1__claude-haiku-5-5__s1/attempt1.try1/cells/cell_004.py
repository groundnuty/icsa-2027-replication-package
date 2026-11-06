import xarray as xr
with fs.open('icsa2027_data_20261101T090944Z/s1z/sst_20100601.nc','rb') as f:
    d=xr.open_dataset(f,engine='h5netcdf').load()
print(d)
print(d.attrs)