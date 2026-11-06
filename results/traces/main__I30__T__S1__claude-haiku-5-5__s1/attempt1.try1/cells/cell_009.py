
import fsspec, time, datetime as dt, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
B='icsa2027_data_20261101T090944Z/s1z/sst_%s.nc'
t=time.time()
with fs.open(B%'20100601','rb') as f:
    ds=xr.open_dataset(f,engine='h5netcdf')
    lat=ds.latitude.values; lon=ds.longitude.values
    la=np.where((lat>=58.69-1e-6)&(lat<=59.89+1e-6))[0]; lo=np.where((lon>=18.69-1e-6)&(lon<=19.89+1e-6))[0]
    print(len(la),len(lo), lat[la[0]],lat[la[-1]],lon[lo[0]],lon[lo[-1]])
    sub=ds.analysed_sst.isel(latitude=slice(la[0],la[-1]+1),longitude=slice(lo[0],lo[-1]+1)).load()
print(time.time()-t, sub.dtype, sub.attrs)
print(np.isfinite(sub.values).sum(), sub.size)
