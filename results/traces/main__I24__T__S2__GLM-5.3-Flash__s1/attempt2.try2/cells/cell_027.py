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
    filled = arr.copy()
    filled[59] = 0.5 * (filled[58] + filled[60])   # NaN only at d60 pre-fill
    loop = circ_smooth31_loop(filled)
    win = circ_smooth31_win(filled)
    print(name, "loop-vs-win max|diff| (sea):", np.abs(loop - win)[:, sea].max())
    print(name, "loop-vs-saved max|diff| (sea):", np.abs(loop - sm)[:, sea].max())
    print(name, "win-vs-saved max|diff| (sea):", np.abs(win - sm)[:, sea].max())
    print(name, "NaN in filled sea cells:", int(np.isnan(filled[:, sea]).sum()))
