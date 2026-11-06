
import fsspec, os, xarray as xr, numpy as np
print(os.path.getsize('/work/sst_s2.nc'))
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds.analysed_sst.attrs); print(ds.analysed_sst.encoding)
print(ds.comment)
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=57.33-1e-6)&(lat<=58.53+1e-6))[0]; lo=np.where((lon>=9.03-1e-6)&(lon<=10.23+1e-6))[0]
print(lat[la[0]],lat[la[-1]],len(la),lon[lo[0]],lon[lo[-1]],len(lo))
t=ds.time.values
print(t[0],t[-1])
