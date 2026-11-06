
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
path='icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f=fs.open(path,'rb')
ds=xr.open_dataset(f,engine='h5netcdf')
v=ds.analysed_sst
print(v.attrs); print(v.encoding)
lat=ds.latitude.values; lon=ds.longitude.values
li=np.where((lat>=57.33-1e-6)&(lat<=58.53+1e-6))[0]; lo=np.where((lon>=9.03-1e-6)&(lon<=10.23+1e-6))[0]
print(lat[li][[0,-1]], lon[lo][[0,-1]], len(li), len(lo))
