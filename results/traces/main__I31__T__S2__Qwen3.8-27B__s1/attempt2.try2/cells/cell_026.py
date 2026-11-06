import numpy as np
from datetime import date, timedelta

z = np.load('/work/stats.npz', allow_pickle=False)
thr = z['thr']; t_dates = z['t_dates']
zz = np.load('/work/read_done.npz', allow_pickle=False)
base = zz['base']; b_dates = zz['b_dates']
la, lo = 40, 5
c = la*60 + lo

bidx = {np.datetime64(d,'D'): k for k, d in enumerate(b_dates)}
md = {}
for d in range(1, 367):
    dt = date(2000,1,1) + timedelta(days=d-1)
    md[d] = (dt.month, dt.day)

bvals = base[:, la, lo].astype(np.float64)
raw_q = np.full(366, np.nan); raw_m = np.full(366, np.nan)
for d in range(1, 367):
    if d == 60: continue
    m, dd = md[d]
    dates = set()
    for y in range(1992, 2003):
        b = date(y, m, dd)
        for k in range(-5, 6):
            t = np.datetime64(b + timedelta(days=k), 'D')
            if t in bidx: dates.add(bidx[t])
    pool = bvals[np.array(sorted(dates))]
    pool = pool[~np.isnan(pool)]
    n = len(pool)
    p = np.sort(pool)
    h = min(max(n*0.9 - 0.5, 0.0), n-1)
    j = int(h); g = h - j
    raw_q[d-1] = p[j] if (g < 1e-15 or j >= n-1) else p[j] + g*(p[j+1]-p[j])
    raw_m[d-1] = pool.mean()
raw_q[59] = (raw_q[58]+raw_q[60])/2; raw_m[59] = (raw_m[58]+raw_m[60])/2

sm = np.array([np.mean([raw_q[(d + k) % 366] for k in range(-15, 16)]) for d in range(366)])
diff = np.abs(sm - thr[c])
print("max |independent-smoothed - stored|:", diff.max(), " at doy", diff.argmax()+1)
d2 = np.where(diff > 1e-9)[0]
print("doys differing count:", len(d2), (d2+1)[:20])
smm = np.array([np.mean([raw_m[(d + k) % 366] for k in range(-15, 16)]) for d in range(366)])
print("clim max diff:", np.abs(smm - z['clim'][c]).max())
