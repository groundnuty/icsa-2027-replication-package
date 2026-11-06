import fsspec, xarray as xr, time, io
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
t=time.time()
with fs.open(base+'/sst_20210601.nc','rb') as f:
    ds=xr.open_dataset(io.BytesIO(f.read()),engine='h5netcdf')
    ds.load()
print(time.time()-t)
print(ds)
print(ds.analysed_sst.attrs)
import numpy as np
lat=ds.latitude.values; lon=ds.longitude.values
m=(lat>=54.39-1e-6)&(lat<=55.59+1e-6); n=(lon>=18.25-1e-6)&(lon<=19.45+1e-6)
print(m.sum(), n.sum(), lat[m][[0,-1]], lon[n][[0,-1]])
a=ds.analysed_sst.values[0][np.ix_(m,n)]
print(np.isfinite(a).mean(), a.dtype, np.nanmin(a), np.nanmax(a))
