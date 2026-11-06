import numpy as np

# independent loop implementation of circular 31-day mean
def circ_smooth31_loop(a):
    n = a.shape[0]
    idx = (np.arange(n)[:, None] + np.arange(-15, 16)[None, :]) % n
    return a[idx].mean(axis=1)

# synthetic check
a = np.arange(366, dtype=np.float64) + 1000.0
r1 = circ_smooth31_loop(a)
# day 1 (idx 0): doys 352..366 -> idx 351..365, day1 -> idx 0, days 2..16 -> idx 1..15
exp0 = np.concatenate([np.arange(351, 366), [0], np.arange(1, 16)])
print("d1 window size:", exp0.size)
print("d1:", r1[0], "expected:", a[exp0].mean(), "match:", abs(r1[0]-a[exp0].mean()) < 1e-9)
# day 366 (idx 365): doys 351..365 -> idx 350..364, center 365, doys 1..15 -> idx 0..14
exp365 = np.concatenate([np.arange(350, 365), [365], np.arange(0, 15)])
print("d366 window size:", exp365.size)
print("d366:", r1[365], "expected:", a[exp365].mean(), "match:", abs(r1[365]-a[exp365].mean()) < 1e-9)

# compare loop vs sliding-window on the REAL threshold/clim arrays
from numpy.lib.stride_tricks import sliding_window_view
thresh_s = np.load("/work/thresh_s.npy")
clim_s = np.load("/work/clim_s.npy")
pad = np.concatenate([thresh_s[-15:], thresh_s, thresh_s[:15]])
sw = sliding_window_view(pad, 31, axis=0).mean(axis=-1)
print("thresh_s loop-vs-window max abs diff:", np.abs(sw - circ_smooth31_loop(thresh_s)).max())

# cross-check clim too
padc = np.concatenate([clim_s[-15:], clim_s, clim_s[:15]])
swc = sliding_window_view(padc, 31, axis=0).mean(axis=-1)
print("clim_s loop-vs-window max abs diff:", np.abs(swc - circ_smooth31_loop(clim_s)).max())

# also verify against original stage-C smoothing code path on raw arrays
thresh_raw = np.load("/work/thresh_raw.npy")
clim_raw = np.load("/work/clim_raw.npy")
for arr, name in ((thresh_raw, "thresh"), (clim_raw, "clim")):
    p = np.concatenate([arr[-15:], arr, arr[:15]])
    w = sliding_window_view(p, 31, axis=0).mean(axis=-1)
    loop = circ_smooth31_loop(arr)
    print(name, "raw->smoothed, window-vs-loop max diff:", np.abs(w - loop).max())
