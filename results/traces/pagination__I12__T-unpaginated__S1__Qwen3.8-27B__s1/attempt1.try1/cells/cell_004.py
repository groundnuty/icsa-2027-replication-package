import fsspec, time
import xarray as xr
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z/s1z'
t0 = time.time()
with fs.open(root+'/sst_20090601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
print('read time:', time.time()-t0)
print(ds)
print('lat range:', float(ds.lat.min()), float(ds.lat.max()))
print('lon range:', float(ds.lon.min()), float(ds.lon.max()))
print('dtypes:', {k: str(v.dtype) for k,v in ds.variables.items()})