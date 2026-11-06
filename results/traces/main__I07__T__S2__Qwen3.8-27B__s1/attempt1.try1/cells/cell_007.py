
import fsspec, h5netcdf, time, numpy as np, xarray as xr, pandas as pd, os
os.makedirs('/tmp/mhw', exist_ok=True)
t0 = time.time()
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
h = h5netcdf.File(f, mode='r')
ds = xr.open_dataset(f, engine='h5netcdf')
tvals = pd.DatetimeIndex(ds['time'].values)
idx = {d: i for i, d in enumerate(tvals)}
e0, e1 = pd.Timestamp('1991-12-27'), pd.Timestamp('2003-01-05')
g0, g1 = pd.Timestamp('2021-06-01'), pd.Timestamp('2021-08-31')
ie0, ie1 = idx[e0], idx[e1] + 1
ig0, ig1 = idx[g0], idx[g1] + 1
lat0, lat1, lon0, lon1 = 48, 108, 353, 413
x = np.asarray(h['analysed_sst'][ie0:ie1, lat0:lat1, lon0:lon1], dtype=np.float64)
y = np.asarray(h['analysed_sst'][ig0:ig1, lat0:lat1, lon0:lon1], dtype=np.float64)
X = x.reshape(ie1-ie0, 3600)
Y = y.reshape(ig1-ig0, 3600)
np.save('/tmp/mhw/ext.npy', X)
np.save('/tmp/mhw/tgt.npy', Y)
np.save('/tmp/mhw/ext_dates.npy', np.asarray(tvals[ie0:ie1]).astype('datetime64[D]').astype('int64'))
np.save('/tmp/mhw/tgt_dates.npy', np.asarray(tvals[ig0:ig1]).astype('datetime64[D]').astype('int64'))
np.save('/tmp/mhw/lat.npy', ds['latitude'].values[lat0:lat1])
np.save('/tmp/mhw/lon.npy', ds['longitude'].values[lon0:lon1])
fin = np.isfinite(X); finY = np.isfinite(Y)
print("ext finite frac: %.4f" % fin.mean())
print("tgt finite frac: %.4f, min %.2f max %.2f" % (finY.mean(), np.nanmin(Y), np.nanmax(Y)))
perday = finY.sum(axis=1)
print("tgt per-day finite min/max:", int(perday.min()), int(perday.max()), "days of 3600 cells")
print("cells with no finite target value:", int((~finY.any(axis=0)).sum()))
print("ext dates: %s .. %s (n=%d); tgt dates: %s .. %s (n=%d)" % (
    pd.Timestamp(ext_dates:=None) if False else str(pd.Timestamp(int(X_dates:=int(np.load('/tmp/mhw/ext_dates.npy')[0]))*1000000000)), "skip", X.shape[0]))
print("saved. total %.1fs" % (time.time()-t0))
ds.close(); h.close(); f.close()
