
import fsspec, datetime as dt, time, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
D='icsa2027_data_20261101T090944Z/s1z'
t=time.time()
with fs.open(f"{D}/sst_20040601.nc",'rb') as f:
    ds=xr.open_dataset(f,engine='h5netcdf')
    lat=ds.latitude.values; lon=ds.longitude.values
    il=np.where((lat>=57.41-1e-6)&(lat<=58.61+1e-6))[0]; jl=np.where((lon>=18.69-1e-6)&(lon<=19.89+1e-6))[0]
    sub=ds.analysed_sst.isel(time=0,latitude=il,longitude=jl).values
print(time.time()-t, sub.shape, lat[il[[0,-1]]], lon[jl[[0,-1]]], np.isfinite(sub).sum())
print(np.diff(lat[:5]), lat.dtype)
