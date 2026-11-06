import numpy as np
z = np.load('/work/stats.npz', allow_pickle=False)
thr = z['thr']; t_dates = z['t_dates']
zz = np.load('/work/read_done.npz', allow_pickle=False)
tgt = zz['tgt'].astype(np.float64)
T, La, Lo = tgt.shape
doy_t = np.array([t_dates[k].astype(object).timetuple().tm_yday for k in range(T)], dtype=int)
sea = np.isfinite(tgt).all(axis=0)
sea_flat = sea.reshape(-1)
c = int(np.argmax(sea_flat))
la, lo = divmod(c, Lo)
s = tgt[:, la, lo]
print("s shape", s.shape, s[:3])
th = thr[c, doy_t]
print("th shape", th.shape, th[:3], "n NaN thr for target doys:", int(np.isnan(thr[c, doy_t]).sum()))
h = s >= thr[c, doy_t]
print("h dtype", h.dtype, "len", len(h), h[:10], "sum", h.sum())
padded = np.concatenate(([False], h, [False]))
print("padded dtype", padded.dtype, "len", padded.shape, "first/last:", padded[0], padded[-1])
d = np.diff(padded)
print("d", d)
print("starts", np.where(d == 1)[0] + 1, "ends", np.where(d == -1)[0])
