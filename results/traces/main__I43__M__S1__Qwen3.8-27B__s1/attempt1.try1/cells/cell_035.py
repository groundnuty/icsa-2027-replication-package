import numpy as np, pickle
meta = pickle.load(open("/tmp/target.pkl","rb"))
T = meta["T"]; sea = meta["sea"]
tc = pickle.load(open("/tmp/thrclim.pkl","rb"))
thr_s = tc["thr_s"]
leap_cum = [0,31,60,91,121,152,182,213,244,274,305,335]
from datetime import date, timedelta
d0=date(2017,6,1); dates=[]; cur=d0
while cur<=date(2017,8,31): dates.append(cur); cur+=timedelta(days=1)
doys = np.array([leap_cum[d.month-1]+d.day for d in dates]) - 1
Tf = T.reshape(92, 3600); sea_flat = sea.reshape(3600)
# verify one point against raw read
il = int(np.argmin(np.abs(meta["lat"][meta["slat"]]-62.96)))
ik = int(np.argmin(np.abs(meta["lon"][meta["slon"]]-18.74)))
print("T[44,il,ik]:", T[44, il, ik], "(raw was 286.82)")
thr_t = thr_s[doys]                       # (92, 3600)
margin = Tf - thr_t                        # (92, 3600)
ms = margin[:, sea_flat]
print("global max margin SST-thr:", ms.max())
top = np.dstack(np.unravel_index(np.argsort(ms, axis=None)[::-1][:10], ms.shape))[0]
for t_, c_ in top:
    l, k = divmod(int(c_), 60)
    print(f"  {dates[t_].isoformat()} cell {int(meta['lat'][meta['slat']][l]):.2f}N {int(meta['lon'][meta['slon']][k]):.2f}E (sub {l},{k}): SST={Tf[t_,c_]:.2f} thr={thr_t[t_,c_]:.2f} margin={ms[t_,c_]:+.4f} K")
# per-date max margin
dm = ms.max(axis=1)
print("best dates:", [(dates[i].isoformat(), round(float(dm[i]),3)) for i in np.argsort(dm)[-5:]])
# hot check incl. equality
print("any margin >= 0:", bool((ms >= 0).any()))
# also with raw unsmoothed threshold for reference
thr_raw_t = tc["thr_raw"][doys]
print("any SST >= raw thr:", bool((Tf >= thr_raw_t)[:, sea_flat].any()))
# baseline July stats for one cell for context
X = np.load("/tmp/X.npy"); Xd = X.reshape(4028, 3600)
P = pickle.load(open("/tmp/pools.pkl","rb"))
c = il*60+ik
vals = Xd[P["pools"][197], c]
print("baseline Jul-15 pool min/max/mean:", np.nanmin(vals), np.nanmax(vals), np.nanmean(vals))
