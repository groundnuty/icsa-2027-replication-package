
import fsspec, h5netcdf, time, numpy as np, xarray as xr, pandas as pd, os
os.makedirs('/tmp/mhw', exist_ok=True)
t0 = time.time()
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
h = h5netcdf.File(f, mode='r')
# time index via xarray (small read)
ds = xr.open_dataset(f, engine='h5netcdf')
tvals = pd.DatetimeIndex(ds['time'].values)
idx = {d: i for i, d in enumerate(tvals)}
e0 = pd.Timestamp('1991-12-27'); e1 = pd.Timestamp('2003-01-05')
g0 = pd.Timestamp('2021-06-01'); g1 = pd.Timestamp('2021-08-31')
ie0, ie1 = idx[e0], idx[e1] + 1
ig0, ig1 = idx[g0], idx[g1] + 1
print("ext slice:", ie0, ie1, "len", ie1-ie0)
print("tgt slice:", ig0, ig1, "len", ig1-ig0)
lat0, lat1, lon0, lon1 = 48, 108, 353, 413
t1 = time.time()
x = np.asarray(h['analysed_sst'][ie0:ie1, lat0:lat1, lon0:lon1], dtype=np.float64)
print("ext read: %.1fs shape %s" % (time.time()-t1, x.shape))
y = np.asarray(h['analysed_sst'][ig0:ig1, lat0:lat1, lon0:lon1], dtype=np.float64)
print("tgt read: %.1fs shape %s" % (time.time()-t1, y.shape))
X = x.reshape(ie1-ie0, 3600)   # cell index = ilat*60 + ilon
Y = y.reshape(ig1-ig0, 3600)
np.save('/tmp/mhw/ext.npy', X)
np.save('/tmp/mhw/tgt.npy', Y)
np.save('/tmp/mhw/ext_dates.npy', tvals[ie0:ie1].asi8.values)
np.save('/tmp/mhw/tgt_dates.npy', tvals[ig0:ig1].asi8.values)
np.save('/tmp/mhw/lat.npy', ds['latitude'].values[lat0:lat1])
np.save('/tmp/mhw/lon.npy', ds['longitude'].values[lon0:lon1])
# sanity
print("ext finite per-day min/max frac:", X.reshape(-1,3600).shape)
fin = np.isfinite(X)
print("ext overall finite frac: %.4f" % fin.mean())
print("tgt finite frac: %.4f, min %.2f max %.2f" % (np.isfinite(Y).mean(), np.nanmin(Y), np.nanmax(Y)))
perday = np.isfinite(Y, axis=1)
print("tgt days with zero finite cells:", int((perday.sum(axis=1)==0).sum()))
print("tgt per-day finite min:", int(perday.sum(axis=1).min()))
landish = ~np.isfinite(Y).any(axis=0)
print("cells with no finite target value:", int(landish.sum()))
print("total: %.1fs" % (time.time()-t0))
ds.close(); h.close(); f.close()
