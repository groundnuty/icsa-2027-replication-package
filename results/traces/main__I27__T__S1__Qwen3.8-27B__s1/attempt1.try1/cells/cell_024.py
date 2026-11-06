
import numpy as np, datetime as dt

thr_s = np.load('/tmp/mhw/thr_s.npy')
clim_s = np.load('/tmp/mhw/clim_s.npy')
A = np.load('/tmp/mhw/target.npy').squeeze(axis=1)
A2 = A.reshape(A.shape[0], -1)
sea2 = np.load('/tmp/mhw/sea2.npy')
tdates = [dt.date(2008,6,1) + dt.timedelta(days=i) for i in range(A.shape[0])]
cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
tdoy = (cum[np.array([d.month for d in tdates])-1] + np.array([d.day for d in tdates])).astype(np.int64)
NC = sea2.size

hot = np.zeros((A2.shape[0], NC), dtype=bool)
for k, d in enumerate(tdoy):
    hot[k] = A2[k] >= thr_s[d-1]
hot = hot & sea2[None, :]
print("hot days total:", int(hot.sum()))
print("hot per day:", hot.sum(axis=1).tolist())
np.save('/tmp/mhw/hot.npy', hot)
