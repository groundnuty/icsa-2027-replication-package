import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

thresh_raw = np.load("/work/thresh_raw.npy")
print("raw d59,d60,d61 cell[10,10]:", thresh_raw[58:61, 10, 10])
print("raw d59,d60,d61 cell[0,0]:", thresh_raw[58:61, 0, 0])
print("raw d59,d60,d61 cell[59,59]:", thresh_raw[58:61, 59, 59])

# correct manual check: doys 135..165 -> indices 134..164 (31 values)
manual = thresh_raw[134:165, 10, 10].mean()

thresh_s = np.load("/work/thresh_s.npy")
print("smooth d150:", thresh_s[149,10,10], "manual(135..165):", manual, "diff:", abs(thresh_s[149,10,10]-manual))

# synthetic wrap check
a = np.arange(366, dtype=np.float64) + 1000.0
pad = np.concatenate([a[-15:], a, a[:15]])
win = sliding_window_view(pad, 31)
res = win.mean(axis=-1)
# day 1 (index 0): mean of doys 352..365 (indices 351..364) and 1..15 (indices 0..14)
exp0 = (np.arange(351, 366) + 1000.0).sum() + (np.arange(0, 15) + 1000.0).sum()
exp0 /= 31.0
print("wrap check d1:", res[0], "expected:", exp0, "match:", abs(res[0]-exp0) < 1e-9)
# day 366 (index 365): doys 351..365 and 1..16
exp365 = (np.arange(350, 365) + 1000.0).sum() + (np.arange(0, 16) + 1000.0).sum()
exp365 /= 31.0
print("wrap check d366:", res[365], "expected:", exp365, "match:", abs(res[365]-exp365) < 1e-9)
# day 100: doys 85..115
exp100 = (np.arange(84, 115) + 1000.0).mean()
print("mid check d100:", res[99], "expected:", exp100, "match:", abs(res[99]-exp100) < 1e-9)

# also verify clim smoothing the same way
clim_raw = np.load("/work/clim_raw.npy")
clim_s = np.load("/work/clim_s.npy")
print("clim smooth d150 vs manual:", clim_s[149,10,10], clim_raw[134:165,10,10].mean())
