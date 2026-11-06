
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f=fs.open(p,'rb')
ds=xr.open_dataset(f,engine='h5netcdf')
print(ds.analysed_sst.attrs)
sub=ds.sel(latitude=slice(60.09,61.29), longitude=slice(20.01,21.21))
print(sub.latitude.size, sub.longitude.size, sub.latitude.values[[0,-1]], sub.longitude.values[[0,-1]])
