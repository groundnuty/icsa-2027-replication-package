import xarray as xr, numpy as np
print('numpy', np.__version__)
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t = ds.time.values
d = np.diff(t).astype('timedelta64[D]')
print('time monotonic unique daily:', np.all(d == np.timedelta64(1,'D')), t[0], t[-1])

lat, lon = ds.latitude.values, ds.longitude.values
lm = (lat >= 54.39) & (lat <= 55.59)
lo = (lon >= 18.25) & (lon <= 19.45)
print('n lat cells', lm.sum(), lat[lm][0], lat[lm][-1])
print('n lon cells', lo.sum(), lon[lo][0], lon[lo][-1])
# any grid values within 1e-4 of the bounds?
for v in np.concatenate([lat, lon]):
    pass
import math
near_lat = [v for v in lat if abs(v-54.39)<1e-6 or abs(v-55.59)<1e-6]
near_lon = [v for v in lon if abs(v-18.25)<1e-6 or abs(v-19.45)<1e-6]
print('values near bounds lat:', near_lat, 'lon:', near_lon)
print('fill value attr:', ds.analysed_sst.encoding)
# quick peek: NaN fraction in region over 2020 target
i0 = int(np.searchsorted(t, np.datetime64('2020-06-01')))
i1 = int(np.searchsorted(t, np.datetime64('2020-08-31')))
blk = ds.analysed_sst.isel(time=slice(i0, i1+1), latitude=np.where(lm)[0], longitude=np.where(lo)[0]).load()
print('block shape', blk.shape)
print('nan frac over target in region:', float(np.isnan(blk.values).mean()))
print('finite-everywhere cells:', int((~np.isnan(blk.values).any(axis=0)).sum()), 'of', blk.shape[1]*blk.shape[2])
print('sample SST values K:', np.nanmean(blk.values), 'min', np.nanmin(blk.values), 'max', np.nanmax(blk.values))
