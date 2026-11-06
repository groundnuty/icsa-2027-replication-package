import h5py, numpy as np
f = h5py.File('/work/sst_s2.nc','r')
d = f['analysed_sst']
print('chunks:', d.chunks, 'dtype:', d.dtype, 'compression:', d.compression)
print('attrs raw:', dict(d.attrs))
f.close()
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values; lon = ds.longitude.values
latm = (lat >= 57.41) & (lat <= 58.61); lonm = (lon >= 18.69) & (lon <= 19.89)
i0 = np.where(latm)[0][0]; j0 = np.where(lonm)[0][0]
print('i0', i0, 'j0', j0)
# sanity: a small slice
sub = ds.analysed_sst.isel(time=slice(0,3), latitude=slice(i0,i0+60), longitude=slice(j0,j0+60))
arr = sub.values
print('shape', arr.shape, 'dtype', arr.dtype)
print('min/max (nan-ignoring, first 3 days region):', np.nanmin(arr), np.nanmax(arr))
print('finite frac region first 3 days:', np.isfinite(arr).mean())
# land fraction in region over full time (sample a few times)
sample = ds.analysed_sst.isel(time=slice(8000,8010), latitude=slice(i0,i0+60), longitude=slice(j0,j0+60)).values
print('sample finite frac:', np.isfinite(sample).mean(), 'min/max', np.nanmin(sample), np.nanmax(sample))