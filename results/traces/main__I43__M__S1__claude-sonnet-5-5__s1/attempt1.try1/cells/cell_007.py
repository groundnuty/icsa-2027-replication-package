import xarray as xr,numpy as np
d=xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20170601.nc',engine='h5netcdf')
la=d.latitude.values;lo=d.longitude.values
li=np.where((la>=62.2499)&(la<=63.4501))[0];oi=np.where((lo>=18.7299)&(lo<=19.9301))[0]
m=xr.open_dataset('output/mhw_mask.nc').load()
m=m.assign_coords(lat=la[li],lon=lo[oi]);m.close()
m.to_netcdf('output/mhw_mask.nc')
print(m.lat.values[[0,-1]],int(m.mhw.sum()))