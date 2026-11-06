import fsspec, xarray as xr, numpy as np, time, pandas as pd, os
print('numpy', np.__version__)
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine="h5netcdf")
lat = ds.latitude.values.astype('float64'); lon = ds.longitude.values.astype('float64')
li = np.nonzero((lat>=59.05)&(lat<=60.25))[0]; lj = np.nonzero((lon>=21.25)&(lon<=22.45))[0]
np.save('/tmp/lat.npy', lat[li]); np.save('/tmp/lon.npy', lon[lj])
np.save('/tmp/time_all.npy', ds.time.values.astype('int64'))

td = pd.to_datetime(ds.time.values)
i0 = int(np.searchsorted(td.values, np.datetime64('1991-12-27')))
i1 = int(np.searchsorted(td.values, np.datetime64('2003-01-05')))
i2 = int(np.searchsorted(td.values, np.datetime64('2014-06-01')))
i3 = int(np.searchsorted(td.values, np.datetime64('2014-08-31')))
np.save('/tmp/idx.npy', np.array([i0,i1,i2,i3]))

t0=time.time()
base = ds.analysed_sst.isel(time=range(i0,i1+1), latitude=li, longitude=lj).values.astype('float64')
print('baseline read %.1fs' % (time.time()-t0), base.shape)
np.save('/tmp/sst_base.npy', base)

t0=time.time()
tgt = ds.analysed_sst.isel(time=range(i2,i3+1), latitude=li, longitude=lj).values.astype('float64')
print('target read %.1fs' % (time.time()-t0), tgt.shape)
np.save('/tmp/sst_target.npy', tgt)

bdates = (ds.time.values[i0:i1+1].astype('datetime64[D]'))
tdates = (ds.time.values[i2:i3+1].astype('datetime64[D]'))
np.save('/tmp/bdates.npy', bdates); np.save('/tmp/tdates.npy', tdates)
print('baseline nan frac %.4f, target nan frac %.4f' % (np.nanmean(~np.isfinite(base)), np.nanmean(~np.isfinite(tgt))))
print('base finite min/max', np.nanmin(base), np.nanmax(base))
print('tgt  finite min/max', np.nanmin(tgt), np.nanmax(tgt))
# sea cells quick check: cells finite on all 92 target days
fin_t = np.isfinite(tgt).all(axis=0)
print('sea cells:', int(fin_t.sum()), 'of', fin_t.size)
os.listdir('/tmp')
