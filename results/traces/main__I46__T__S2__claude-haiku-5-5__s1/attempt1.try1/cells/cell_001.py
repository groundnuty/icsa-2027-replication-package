
import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
print(fs.ls('icsa2027_data_20261101T090944Z/s2z', detail=False))
f=fs.open(p,'rb')
ds=xr.open_dataset(f,engine='h5netcdf')
print(ds)
