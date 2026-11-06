import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
t=time.time()
with fs.open(base+'sst_20070601.nc','rb') as f:
    ds=xr.open_dataset(f,engine='h5netcdf').load()
print('read s',time.time()-t)
print(ds.analysed_sst.attrs)
print(ds.attrs['comment'])
lat=ds.latitude.values; lon=ds.longitude.values
print(np.diff(lat)[:3], np.unique(np.round(np.diff(lat),6)), np.unique(np.round(np.diff(lon),6)))
la=np.where((lat>=54.81-1e-6)&(lat<=56.01+1e-6))[0]; lo=np.where((lon>=19.61-1e-6)&(lon<=20.81+1e-6))[0]
print(len(la),len(lo), lat[la[0]],lat[la[-1]],lon[lo[0]],lon[lo[-1]])
a=ds.analysed_sst.values[0][np.ix_(la,lo)]
print(np.isnan(a).sum(), a.size, np.nanmin(a), np.nanmax(a))