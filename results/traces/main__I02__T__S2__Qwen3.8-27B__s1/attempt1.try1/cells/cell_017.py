import numpy as np, pickle
from datetime import date, timedelta
z = np.load('work/sst.npz')
ST = z['ST']; tt = z['tt']; SB = z['SB']; tb = z['tb']
z2 = np.load('work/thr.npz')
thr_s, sea = z2['thr_s'], z2['sea']
n_cells = 3600
STf = ST.reshape(92, n_cells)
print("tt[0], tt[-1]:", tt[0].astype(str), tt[-1].astype(str), "n:", len(tt), "unique:", len(np.unique(tt)))
doy_md = {}
d = date(2004,1,1)
for k in range(366):
    doy_md[k+1] = (d.month, d.day); d += timedelta(days=1)
md2d = {v:k for k,v in doy_md.items()}
t_doys = np.array([md2d[(date.fromisoformat(ts.astype('datetime64[D]').astype(str)).month,
                         date.fromisoformat(ts.astype('datetime64[D]').astype(str)).day)] for ts in tt])
hot = STf >= thr_s[:, t_doys-1].T
print("total hot cell-days:", int(hot[:, sea].sum()))
byday = {}
for i in range(92):
    cs = np.where(hot[i] & sea)[0]
    if len(cs): byday[str(tt[i].astype('datetime64[D]'))] = cs.tolist()
for k in sorted(byday): print(k, "n=", len(byday[k]), "cells:", byday[k][:12])

# per-cell max consecutive hot days
maxrun = np.zeros(n_cells, int)
for c in range(n_cells):
    r = 0; best = 0
    for v in hot[:, c]:
        r = r + 1 if v else 0
        best = max(best, r)
    maxrun[c] = best
print("max consecutive hot days over all cells:", int(maxrun.max()))
top = np.argsort(maxrun)[::-1][:8]
for c in top:
    if maxrun[c] == 0: break
    days = [str(tt[i].astype('datetime64[D]')) for i in np.where(hot[:, c])[0]]
    print("cell", c, "lat", float(z['lat'][c//60]), "lon", float(z['lon'][c%60]), "maxrun", maxrun[c], "hot days:", days)
