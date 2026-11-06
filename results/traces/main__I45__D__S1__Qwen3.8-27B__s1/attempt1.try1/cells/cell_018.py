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

def hazen5_manual(vals):  # HF type 5 (Blom): 0-based position n*p - 0.5
    x = np.sort(vals); n = len(x)
    h = n*0.9 - 0.5
    j = int(np.floor(h)); g = h - j
    if j < 0: return x[0]
    if j >= n-1: return x[n-1] if j >= n else x[n-1]
    return (1-g)*x[j] + g*x[min(j+1, n-1)]

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

thr = np.load('/work/thr.npy'); sea = np.load('/work/sea.npy')
sea_cells = np.where(sea)[0]
rng = np.random.default_rng(7)
mism = 0
for trial in range(60):
    c = sea_cells[rng.integers(len(sea_cells))]
    d = int(rng.integers(1,367)); d = 60 if d==60 else d
    if d == 60:  # check fill rule + smoothing instead
        continue
    idx = pool_for(d)
    v = base_arr[idx, c]
    v = v[np.isfinite(v)]
    man = hazen5_manual(v)
    ref = np.nanpercentile(base_arr[idx,:].T, 90, axis=1, method='hazen')[c]
    if abs(man - ref) > 1e-9:
        mism += 1; print("MISMATCH c",c,"d",d,man,ref)
print("mismatches over 60 random (cell,d):", mism)

# also verify day-60 fill and smoothing for one cell
c = sea_cells[0]
d = 153
# recompute raw for 59,61,60 manually
raw60 = np.full(366, np.nan)
for dd in (59,61):
    idx = pool_for(dd)
    v = base_arr[idx, c]
    v = v[np.isfinite(v)]
    raw60[dd-1] = hazen5_manual(v)
raw60[59] = 0.5*(raw60[58]+raw60[60])
# smoothing at 60 (idx 59): mean of raw60[44..75]
sm60 = raw60[44:75].mean()
print("manual smoothed thr at d=60, cell", c, ":", sm60, " stored:", thr[c,59])
print("diff:", abs(sm60 - thr[c,59]))
