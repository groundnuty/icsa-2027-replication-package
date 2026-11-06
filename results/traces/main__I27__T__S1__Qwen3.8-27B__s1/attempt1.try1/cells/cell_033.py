
import numpy as np
thr_raw = np.load('/tmp/mhw/thr_raw.npy').copy(); clim_raw = np.load('/tmp/mhw/clim_raw.npy').copy()
thr_s = np.load('/tmp/mhw/thr_s.npy'); clim_s = np.load('/tmp/mhw/clim_s.npy')
thr_raw[59] = (thr_raw[58] + thr_raw[60]) / 2.0
clim_raw[59] = (clim_raw[58] + clim_raw[60]) / 2.0
idx = (np.arange(366)[:, None] + np.arange(-15, 16)[None, :]) % 366
def eq(a, b):
    return np.array_equal(np.nan_to_num(a, nan=-123.456), np.nan_to_num(b, nan=-123.456))
print("thr_s reproducible (nan-aware):", eq(thr_s, thr_raw[idx].mean(axis=1)))
print("clim_s reproducible (nan-aware):", eq(clim_s, clim_raw[idx].mean(axis=1)))
