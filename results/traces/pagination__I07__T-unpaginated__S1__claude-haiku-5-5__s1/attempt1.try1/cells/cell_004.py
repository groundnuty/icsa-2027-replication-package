import time
print(ds.analysed_sst.attrs)
print(ds.latitude.values[:3], ds.latitude.values[-1], ds.longitude.values[-1])
t=time.time()
with fs.open(files[10000],'rb') as f:
    d2=xarray.open_dataset(f, engine='h5netcdf').load()
print(time.time()-t, d2.time.values, np.nanmean(d2.analysed_sst.values))
print(files[10000])
