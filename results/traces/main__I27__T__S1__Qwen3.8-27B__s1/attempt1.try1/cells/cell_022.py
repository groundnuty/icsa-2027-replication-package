
import numpy as np, datetime as dt, time

thr_raw = np.load('/tmp/mhw/thr_raw.npy')
clim_raw = np.load('/tmp/mhw/clim_raw.npy')
A = np.load('/tmp/mhw/target.npy').squeeze(axis=1)
tdates = [dt.date(2008,6,1) + dt.timedelta(days=i) for i in range(A.shape[0])]
cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
tdoy = (cum[np.array([d.month for d in tdates])-1] + np.array([d.day for d in tdates])).astype(np.int64)
print("target doy range:", tdoy.min(), tdoy.max())

NC = thr_raw.shape[1]
sea = np.all(np.isfinite(A), axis=0)

# day 60 = mean of 59 and 61 (before smoothing)
thr_raw[59] = (thr_raw[58] + thr_raw[60]) / 2.0
clim_raw[59] = (clim_raw[58] + clim_raw[60]) / 2.0

# centred 31-day circular moving mean
idx = (np.arange(366)[:, None] + np.arange(-15, 16)[None, :]) % 366
thr_s = thr_raw[idx].mean(axis=1)   # (366, NC)
clim_s = clim_raw[idx].mean(axis=1)
print("smoothed ok; NaN rows thr_s:", np.where(~np.isfinite(thr_s).all(axis=1))[0][:10], "...")
# check sea cells finite everywhere after smoothing
print("sea cells finite thr_s all doys:", np.isfinite(thr_s[:, sea]).all(), " clim_s:", np.isfinite(clim_s[:, sea]).all())

# hot mask
hot = np.zeros((A.shape[0], NC), dtype=bool)
for k, d in enumerate(tdoy):
    hot[k] = A[k] >= thr_s[d-1]
hot = hot & sea[None, :]
print("hot days total:", hot.sum(), " hot per day:", hot.sum(axis=1))
np.save('/tmp/mhw/hot.npy', hot)
np.save('/tmp/mhw/thr_s.npy', thr_s); np.save('/tmp/mhw/clim_s.npy', clim_s)
