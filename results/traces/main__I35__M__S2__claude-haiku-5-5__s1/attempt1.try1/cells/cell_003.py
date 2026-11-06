
import xarray as xr, numpy as np
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
li=np.where((lat>=59.93-1e-6)&(lat<=61.13+1e-6))[0]; lj=np.where((lon>=18.69-1e-6)&(lon<=19.89+1e-6))[0]
print(len(li),len(lj),lat[li[0]],lat[li[-1]],lon[lj[0]],lon[lj[-1]])
print(np.diff(lat[li][:5]), ds.time.values[:2], ds.time.size)
