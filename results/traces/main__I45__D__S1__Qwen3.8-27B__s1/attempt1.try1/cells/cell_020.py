import numpy as np, datetime as dt
def date_list(start, end):
    d = start; out=[]
    while d <= end:
        out.append(d); d += dt.timedelta(days=1)
    return out
base_dates = date_list(dt.date(1991,12,27), dt.date(2003,1,5))
base_idx = {x:i for i,x in enumerate(base_dates)}
base_arr = np.empty((4028,3600))
for i, dd in enumerate(base_dates):
    base_arr[i] = np.load(f"/work/region/{dd:%Y%m%d}.npy").ravel()

md = [31,29,31,30,31,30,31,31,30,31,30,31]; cum=[0]
for x in md: cum.append(cum[-1]+x)
def md_of(doy):
    for m in range(12):
        if cum[m] < doy <= cum[m+1]: return m+1, doy-cum[m]
def pool_for(d):
    m, day = md_of(d); s=set()
    for y in range(1992,2003):
        B = dt.date(y,m,day)
        for k in range(-5,6):
            T=B+dt.timedelta(days=k)
            if dt.date(1991,12,27)<=T<=dt.date(2003,1,5): s.add(base_idx[T])
    return np.array(sorted(s))

def hazen5(x):
    x = np.sort(x); n = len(x); h = n*0.9 - 0.5
    j = int(np.floor(h)); g = h - j
    if j >= n-1: return x[n-1]
    if j < 0: return x[0]
    return (1-g)*x[j] + g*x[j+1]

c = 5
raw = np.full(366, np.nan)
for d in range(1,367):
    if d == 60: continue
    v = base_arr[pool_for(d), c]
    v = v[np.isfinite(v)]
    raw[d-1] = hazen5(v)
raw[59] = 0.5*(raw[58]+raw[60])
ext = np.concatenate([raw[-15:], raw, raw[:15]])
sm = np.array([ext[i:i+31].mean() for i in range(366)])
thr = np.load('/work/thr.npy')
print("max abs diff full smoothed threshold, cell 5:", np.abs(sm - thr[5]).max())
print("stored[59]:", thr[5,59], " manual:", sm[59])

# same for climatology quickly
rawc = np.full(366, np.nan)
for d in range(1,367):
    if d == 60: continue
    v = base_arr[pool_for(d), c]; v = v[np.isfinite(v)]
    rawc[d-1] = v.mean()
rawc[59] = 0.5*(rawc[58]+rawc[60])
extc = np.concatenate([rawc[-15:], rawc, rawc[:15]])
smc = np.array([extc[i:i+31].mean() for i in range(366)])
cli = np.load('/work/cli.npy')
print("max abs diff full smoothed climatology, cell 5:", np.abs(smc - cli[5]).max())
