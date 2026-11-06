print(ds.analysed_sst.attrs); print(ds.analysed_sst.encoding)
print(ds.latitude.values[:3], ds.longitude.values[:3])
import time
t=time.time()
f2=fs.open(files[names.index('sst_20120601.nc')],'rb')
d2=xarray.open_dataset(f2,engine='h5netcdf')
print(time.time()-t, d2.time.values)