
import numpy as np, datetime as dt

thr_raw = np.load('/tmp/mhw/thr_raw.npy')
clim_raw = np.load('/tmp/mhw/clim_raw.npy')
A = np.load('/tmp/mhw/target.npy').squeeze(axis=1)
tdates = [dt.date(2008,6,1) + dt.timedelta(days=i) for i in range(A.shape[0])]
cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
tdoy = (cum[np.array([d.month for d in tdates])-1] + np.array([d.day for d in tdates])).astype(np.int64)

NC = thr_raw.shape[1]
sea2 = np.all(np.isfinite(A), axis=0).reshape(-1)

# verify sea cells finite for all target doys 153..244
print("sea cells finite thr_raw for doys 153..244:", np.isfinite(thr_raw[152:245][:, sea2]).all())

thr_raw[59] = (thr_raw[58] + thr_raw[60]) / 2.0
clim_raw[59] = (clim_raw[58] + clim_raw[60]) / 2.0

idx = (np.arange(366)[:, None] + np.arange(-15, 16)[None, :]) % 366
thr_s = thr_raw[idx].mean(axis=1)
clim_s = clim_raw[idx].mean(axis=1)
print("sea cells finite thr_s all 366 doys:", np.isfinite(thr_s[:, sea2]).all(), " clim_s:", np.isfinite(clim_s[:, sea2]).all())

hot = np.zeros((A.shape[0], NC), dtype=bool)
for k, d in enumerate(tdoy):
    hot[k] = A[k] >= thr_s[d-1]
hot = hot & sea2[None, :]
print("hot days total:", int(hot.sum()))
print("hot per day:", hot.sum(axis=1))
np.save('/tmp/mhw/hot.npy', hot)
np.save('/tmp/mhw/thr_s.npy', thr_s); np.save('/tmp/mhw/clim_s.npy', clim_s)
np.save('/tmp/mhw/sea2.npy', sea2)
