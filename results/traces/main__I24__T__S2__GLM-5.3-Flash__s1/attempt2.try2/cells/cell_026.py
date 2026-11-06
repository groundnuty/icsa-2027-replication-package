import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

sea = np.load("/work/sea.npy")
thresh_raw = np.load("/work/thresh_raw.npy")
clim_raw = np.load("/work/clim_raw.npy")
thresh_s = np.load("/work/thresh_s.npy")
clim_s = np.load("/work/clim_s.npy")

def circ_smooth31_loop(a):
    n = a.shape[0]
    idx = (np.arange(n)[:, None] + np.arange(-15, 16)[None, :]) % n
    return a[idx].mean(axis=1)

def circ_smooth31_win(a):
    p = np.concatenate([a[-15:], a, a[:15]])
    return sliding_window_view(p, 31, axis=0).mean(axis=-1)

for name, arr, sm in (("thresh", thresh_raw, thresh_s), ("clim", clim_raw, clim_s)):
    loop = circ_smooth31_loop(arr)
    win = circ_smooth31_win(arr)
    d1 = np.abs(loop - win)[:, sea].max()
    d2 = np.abs(loop - sm)[:, sea].max()
    d3 = np.abs(win - sm)[:, sea].max()
    print(name, "loop-vs-win:", d1, "loop-vs-saved:", d2, "win-vs-saved:", d3)
    # any NaN in sea cells?
    print(name, "NaN in sea cells (smoothed):", int(np.isnan(sm[:, sea]).sum()),
          "finite min/max:", float(np.nanmin(sm[:, sea])), float(np.nanmax(sm[:, sea])))
    print(name, "NaN in sea cells (raw):", int(np.isnan(arr[:, sea]).sum()))
