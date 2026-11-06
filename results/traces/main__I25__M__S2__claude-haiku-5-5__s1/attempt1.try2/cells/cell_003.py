
import xarray as xr, numpy as np
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=57.57)&(lat<=58.77))[0]; lo=np.where((lon>=10.25)&(lon<=11.45))[0]
print(len(la),len(lo),lat[la[0]],lat[la[-1]],lon[lo[0]],lon[lo[-1]])
sub=ds.isel(latitude=la,longitude=lo)
base=sub.sel(time=slice('1991-12-27','2003-01-05')).analysed_sst.load()
tgt=sub.sel(time=slice('2016-06-01','2016-08-31')).analysed_sst.load()
print(base.shape,tgt.shape, base.time.values[[0,-1]], tgt.time.values[[0,-1]])
