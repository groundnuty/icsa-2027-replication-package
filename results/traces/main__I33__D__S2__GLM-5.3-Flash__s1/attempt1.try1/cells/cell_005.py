import numpy as np, h5py
import xarray as xr
ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
t = ds.time.values; lat = ds.latitude.values; lon = ds.longitude.values
def tidx(datestr): return int(np.searchsorted(t, np.datetime64(datestr)))
i_e0, i_e1 = tidx('1991-12-27'), tidx('2003-01-05')+1
i_t0, i_t1 = tidx('2014-06-01'), tidx('2014-08-31')+1
ls, le, os_, oe = 278, 338, 613, 673

f = h5py.File('/work/s2z/sst_s2.nc', 'r'); dset = f['analysed_sst']
ext = np.array(dset[i_e0:i_e1, ls:le, os_:oe], dtype=np.float64)   # (4028,60,60)
tgt = np.array(dset[i_t0:i_t1, ls:le, os_:oe], dtype=np.float64)   # (92,60,60)
f.close()
np.save('/work/ext.npy', ext); np.save('/work/tgt.npy', tgt)
print(ext.shape, tgt.shape)

ext_dates = t[i_e0:i_e1]; tgt_dates = t[i_t0:i_t1]
print('ext', str(ext_dates[0])[:10], str(ext_dates[-1])[:10], 'contig', np.all(np.diff(ext_dates)==np.timedelta64(1,'D')))
print('tgt', str(tgt_dates[0])[:10], str(tgt_dates[-1])[:10], 'contig', np.all(np.diff(tgt_dates)==np.timedelta64(1,'D')))
print('baseline NaN fraction:', np.isnan(ext).mean())
print('target  NaN fraction:', np.isnan(tgt).mean())
print('target NaN count per day (first 10):', np.isnan(tgt).sum(axis=(1,2))[:10])
print('per-cell target NaNs > 0:', (np.isnan(tgt).sum(axis=0) > 0).sum())
# any weird values?
print('ext min/max (finite):', np.nanmin(ext), np.nanmax(ext))
print('tgt min/max (finite):', np.nanmin(tgt), np.nanmax(tgt))
# which baseline dates have full NaN planes?
nan_days_ext = np.isnan(ext).sum(axis=(1,2))
print('baseline days with any NaN:', (nan_days_ext>0).sum(), 'full-NaN days:', (nan_days_ext==3600).sum())