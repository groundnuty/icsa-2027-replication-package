import numpy as np
z = np.load('/work/stats.npz', allow_pickle=False)
thr = z['thr']; t_dates = z['t_dates']
zz = np.load('/work/read_done.npz', allow_pickle=False)
tgt = zz['tgt'].astype(np.float64)
T, La, Lo = tgt.shape
C = La * Lo
doy_t = np.array([t_dates[k].astype(object).timetuple().tm_yday for k in range(T)], dtype=int)
sea_flat = np.isfinite(tgt).all(axis=0).reshape(-1)

# hot matrix and per-cell max run
def true_runs(x):
    Tn = len(x)
    d = np.diff(x.astype(np.int8))
    s = np.where(d == 1)[0] + 1
    e = np.where(d == -1)[0] + 1
    if x[0]: s = np.concatenate(([0], s))
    if x[-1]: e = np.concatenate((e, [Tn]))
    return s, e

hot = np.zeros((C, T), bool)
for c in range(C):
    if not sea_flat[c]: continue
    la, lo = divmod(c, Lo)
    hot[c] = tgt[:, la, lo] >= thr[c, doy_t]

print("hot cell-days:", int(hot.sum()))
maxrun = np.zeros(C, int)
for c in range(C):
    if not sea_flat[c]: continue
    s, e = true_runs(hot[c])
    if len(s):
        maxrun[c] = (e - s).max()
print("max hot run length: max=%d, n cells with run>=5: %d, >=3: %d, >=2: %d" % (
    maxrun.max(), (maxrun>=5).sum(), (maxrun>=3).sum(), (maxrun>=2).sum()))

# where are the hot days?
cells_with_hot = np.where(hot.sum(axis=1) > 0)[0]
print("cells with any hot day:", len(cells_with_hot))
from collections import Counter
per = hot.sum(axis=1)
print("distribution of hot days per cell:", dict(sorted(Counter(per[per>0].tolist()).items())))
# top cells
top = cells_with_hot[np.argsort(-per[cells_with_hot])[:8]]
for c in top:
    la, lo = divmod(c, Lo)
    days = np.where(hot[c])[0]
    print(f"cell({la},{lo}) lat={z['lat_vals'][la]:.2f} lon={z['lon_vals'][lo]:.2f} hotdays={per[c]}: "
          + ", ".join(f"{str(t_dates[k])[:10]}(sst{tgt[k,la,lo]:.1f}/thr{thr[c,doy_t[k]]:.1f})" for k in days[:12]))
# hottest period: region-wide mean SST - climatology curve
clim = z['clim']
mean_sst = np.nanmean(tgt.reshape(T, -1), axis=1)
mean_clim = np.nanmean(clim[:, doy_t], axis=0)
print("\ndate  region_meanSST  region_meanClim  diff(K)")
for k in range(0, T, 7):
    print(str(t_dates[k])[:10], f"{mean_sst[k]:.2f}", f"{mean_clim[k]:.2f}", f"{mean_sst[k]-mean_clim[k]:+.2f}")
