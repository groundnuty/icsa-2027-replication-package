
import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
t=time.time()
with fs.open(f'{base}/sst_20130601.nc','rb') as f:
    ds=xr.open_dataset(f,engine='h5netcdf'); ds.load()
print(time.time()-t)
print(ds.time.values, ds.analysed_sst.attrs, ds.analysed_sst.encoding)
lat=ds.latitude.values; lon=ds.longitude.values
print(lat[:3], np.diff(lat)[:3], lon[:3], np.diff(lon)[:3])
la=np.where((lat>=64.39)&(lat<=65.59))[0]; lo=np.where((lon>=23.41)&(lon<=24.61))[0]
print(len(la),len(lo), lat[la][[0,-1]], lon[lo][[0,-1]])
sub=ds.analysed_sst.values[0][np.ix_(la,lo)]
print(np.isfinite(sub).sum(), sub.size, np.nanmin(sub), np.nanmax(sub))
