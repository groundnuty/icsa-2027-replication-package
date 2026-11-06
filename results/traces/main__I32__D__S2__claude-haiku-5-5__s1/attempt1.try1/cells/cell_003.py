
import fsspec, os, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
ds = xr.open_dataset('/work/sst.nc', engine='h5netcdf')
print(ds.attrs['comment'])
print(ds.analysed_sst.encoding)
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=59.05)&(lat<=60.25))[0]; lo=np.where((lon>=21.25)&(lon<=22.45))[0]
print(lat[la].min(),lat[la].max(),len(la), lon[lo].min(),lon[lo].max(),len(lo))
