import numpy as np
z = np.load('/work/region.npz'); s = np.load('/work/doy_stats.npz')
base_sst = z['base_sst']; rc = s['raw_clim']; st = s['sm_thresh']; tgt_doy = s['target_doy']
import datetime
base_dates = [datetime.date.fromisoformat(x) for x in z['base_dates']]
CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
doy = np.array([CUM[d.month-1]+d.day for d in base_dates])
is_anchor = np.zeros(len(base_dates), bool); is_anchor[5:-5] = True
centers = np.where(is_anchor & (doy == 153))[0]

finite_all = np.all(np.isfinite(s['raw_thresh']), axis=0)
col = int(np.where(finite_all)[0][3])
r, cc = divmod(col, 60)
idx = np.concatenate([np.arange(c-5, c+6) for c in centers])
vals = base_sst[idx, r, cc].astype(np.float64)
vf = vals[np.isfinite(vals)]

def hazen(p, q):
    x = np.sort(q); n = len(x)
    h = n*p + 0.5
    k = int(np.floor(h)); g = h - k
    if k <= 0: 
        if g == 0: return x[0]
        return x[0] + (x[1]-x[0])*g
    if k >= n: return x[-1]
    return x[k-1] + (x[k]-x[k-1])*g

print("n pool:", len(vf))
print("manual hazen thr:", hazen(0.9, vf))
print("raw stored thr :", s['raw_thresh'][152, col])
print("manual mean    :", vf.mean(), " raw stored clim:", rc[152, col])
print("np nanquantile :", np.nanquantile(vals, 0.9, method='hazen'))

tgt = z['tgt_sst']
d0 = tgt_doy[0]
print("day0 =", z['tgt_dates'][0], "doy", d0, "sst:", tgt[0, r, cc], "smoothed thr:", st[d0-1, col], "hot:", tgt[0,r,cc] >= st[d0-1, col])
