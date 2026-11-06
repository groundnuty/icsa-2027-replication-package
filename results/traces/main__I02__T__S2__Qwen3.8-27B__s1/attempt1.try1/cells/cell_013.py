import numpy as np
from datetime import date
z = np.load('work/sst.npz')
ST = z['ST']; tb = z['tb']; tt = z['tt']
z2 = np.load('work/thr.npz')
thr_s, clim_s, sea, thr = z2['thr_s'], z2['clim_s'], z2['sea'], z2['thr']
n_cells = 3600
STf = ST.reshape(92, n_cells)
SBf = z['SB'].reshape(4028, n_cells)

c = 1799  # central cell
print("cell", c, "sea:", sea[c], "lat/lon:", z['lat'][1799//60%60 if False else (c//60)%60].item(), )
latv = z['lat'][c//60]; lonv = z['lon'][c%60]
print("lat", float(latv), "lon", float(lonv))
print("target SST 2004-07-15 (doy 197):", STf[45, c], " thr:", thr_s[c, 196], " clim:", clim_s[c, 196])
print("target SST range (finite):", np.nanmin(STf[:, c]), np.nanmax(STf[:, c]))
# baseline climatology for this cell: mean of pool around doy 197 vs target
import pickle
with open('work/pool_idx.pkl','rb') as fh: pool_idx = pickle.load(fh)
pool197 = SBf[pool_idx[197], c]
print("pool197: n=%d min=%.2f max=%.2f mean=%.2f p90=%.2f" % (np.isfinite(pool197).sum(), np.nanmin(pool197), np.nanmax(pool197), np.nanmean(pool197), np.nanquantile(pool197, 0.9, method='hazen')))
print("thr raw (unsmoothed) doy197:", thr[c, 196])
# difference distribution
diff = STf[:, c] - thr_s[c, t_doys-1] if False else None
md_to_doy = None
from datetime import timedelta
doy_md = {}
d = date(2004,1,1)
for k in range(366):
    doy_md[k+1] = (d.month, d.day); d += timedelta(days=1)
md2d = {v:k for k,v in doy_md.items()}
t_doys = np.array([md2d[date.fromisoformat(ts.astype('datetime64[D]').astype(str)).__class__ and tuple(date.fromisoformat(ts.astype('datetime64[D]').astype(str))[0:2])] for ts in tt])
diff = STf[:, c] - thr_s[c, t_doys-1]
print("diff (SST-thr) over target: min %.2f median %.2f max %.2f" % (np.nanmin(diff), np.nanmedian(diff), np.nanmax(diff)))
print("hot days for this cell:", int((diff >= 0).sum()))
# overall
diffs_all = STf - thr_s[:, t_doys-1].T
print("all cells diff: min %.2f median %.2f max %.2f" % (np.nanmin(diffs_all), np.nanmedian(diffs_all), np.nanmax(diffs_all)))
print("fraction >= 0 (sea):", float((diffs_all[:, sea] >= 0).mean()))
