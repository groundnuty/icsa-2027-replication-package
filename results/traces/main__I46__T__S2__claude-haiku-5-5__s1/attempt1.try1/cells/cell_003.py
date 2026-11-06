
import numpy as np, fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f=fs.open(p,'rb')
ds=xr.open_dataset(f,engine='h5netcdf')
v=ds.analysed_sst
print(v.attrs, v.encoding)
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=64.39-1e-6)&(lat<=65.59+1e-6))[0]; lo=np.where((lon>=23.41-1e-6)&(lon<=24.61+1e-6))[0]
print(len(la),len(lo),lat[la[[0,-1]]],lon[lo[[0,-1]]])
