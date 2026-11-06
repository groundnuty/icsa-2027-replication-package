
import numpy as np
thr_raw = np.load('/tmp/mhw/thr_raw.npy').copy()
clim_raw = np.load('/tmp/mhw/clim_raw.npy').copy()
thr_s = np.load('/tmp/mhw/thr_s.npy'); clim_s = np.load('/tmp/mhw/clim_s.npy')
thr_raw[59] = (thr_raw[58] + thr_raw[60]) / 2.0
clim_raw[59] = (clim_raw[58] + clim_raw[60]) / 2.0
idx = (np.arange(366)[:, None] + np.arange(-15, 16)[None, :]) % 366
thr_s2 = thr_raw[idx].mean(axis=1)
clim_s2 = clim_raw[idx].mean(axis=1)
print("thr_s reproducible:", np.array_equal(thr_s, thr_s2))
print("clim_s reproducible:", np.array_equal(clim_s, clim_s2))
c = 0
print("idx59 check (filled):", np.isclose(thr_s[59,c], thr_raw[idxw59 if False else [(59+j)%366 for j in range(-15,16)],c].mean()))
