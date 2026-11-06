
import time
t=time.time()
with fs.open('icsa2027_data_20261101T090944Z/s1z/sst_20140615.nc','rb') as f:
    d=xr.open_dataset(f,engine='h5netcdf').load()
print(time.time()-t)
print(d.analysed_sst.attrs, d.analysed_sst.encoding)
import numpy as np
lat=d.latitude.values; lon=d.longitude.values
ri=np.where((lat>=54.17-1e-6)&(lat<=55.37+1e-6))[0]; ci=np.where((lon>=13.25-1e-6)&(lon<=14.45+1e-6))[0]
print(len(ri),len(ci), lat[ri[[0,-1]]], lon[ci[[0,-1]]])
sub=d.analysed_sst.values[0][np.ix_(ri,ci)]
print(np.isnan(sub).sum(), sub.size, np.nanmin(sub), np.nanmax(sub))
