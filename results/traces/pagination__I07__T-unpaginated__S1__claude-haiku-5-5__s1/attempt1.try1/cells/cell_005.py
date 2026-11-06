import fsspec, re, xarray, numpy as np, time
fs = fsspec.filesystem('onedata')
files = fs.ls('icsa2027_data_20261101T090944Z/s1z', detail=False)
with fs.open(files[0],'rb') as f:
    ds=xarray.open_dataset(f, engine='h5netcdf').load()
print(ds.analysed_sst.attrs)
print(ds.latitude.values[:3], ds.latitude.values[-1], ds.longitude.values[-1])
t=time.time()
with fs.open(files[10000],'rb') as f:
    d2=xarray.open_dataset(f, engine='h5netcdf').load()
print(time.time()-t, d2.time.values, np.nanmean(d2.analysed_sst.values), files[10000])
