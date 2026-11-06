import xarray as xr, numpy as np, os, time
P='/data/icsa2027_data_20261101T090944Z/s1z/'
d=xr.open_dataset(P+'sst_19820101.nc',engine='h5netcdf')
lat=d.latitude.values; lon=d.longitude.values
li=np.where((lat>=58.69-1e-6)&(lat<=59.89+1e-6))[0]; lo=np.where((lon>=18.69-1e-6)&(lon<=19.89+1e-6))[0]
print(len(li),len(lo),lat[li[0]],lat[li[-1]],lon[lo[0]],lon[lo[-1]])
t=time.time()
x=xr.open_dataset(P+'sst_20170615.nc',engine='h5netcdf')
s=x.analysed_sst.values[0,li[0]:li[-1]+1,lo[0]:lo[-1]+1]
print(time.time()-t, s.shape, np.isnan(s).sum())