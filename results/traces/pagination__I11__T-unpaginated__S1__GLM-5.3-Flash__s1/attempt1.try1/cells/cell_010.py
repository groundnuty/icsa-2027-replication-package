import numpy as np, json
raw_thresh = np.load('cache/raw_thresh.npy'); raw_clim = np.load('cache/raw_clim.npy')

def circ_smooth31_cumsum(a):
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.cumsum(pad, axis=0); c = np.concatenate([np.zeros_like(c[:1]), c], axis=0)
    return (c[31:] - c[:-31]) / 31.0

def circ_smooth31_direct(a):
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)
    win = np.stack([pad[i:i+31] for i in range(366)], axis=0)   # (366, 31, ...)
    return win.mean(axis=1)

for name, arr in [('thresh', raw_thresh), ('clim', raw_clim)]:
    s1 = circ_smooth31_cumsum(arr); s2 = circ_smooth31_direct(arr)
    diff = np.abs(s1 - s2)
    print(name, 'max abs diff cumsum vs direct:', diff.max(), '| n differing:', int((diff > 0).sum()))
    pad = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    for i in [0, 1, 59, 182, 350, 365]:
        assert np.array_equal(pad[i:i+31].mean(axis=0), s2[i]), (name, i)
    print(name, 'direct matches manual window mean exactly at all probe indices')
