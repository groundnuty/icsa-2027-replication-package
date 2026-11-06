
import fsspec,xarray as xr
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(fs.open(p,'rb'),engine='h5netcdf')
print(ds)
print(ds.time.values[[0,-1]],ds.lat.values[:3],ds.lon.values[:3])
