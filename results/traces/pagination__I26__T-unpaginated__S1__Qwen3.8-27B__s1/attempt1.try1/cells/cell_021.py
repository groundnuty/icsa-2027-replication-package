import numpy as np, json, warnings
from datetime import date, timedelta
warnings.filterwarnings("ignore")

z = np.load('/work/cache/data.npz')
A_base = z['A_base'].astype(np.float64)
A_tgt  = z['A_tgt'].astype(np.float64)
dates = json.load(open('/work/cache/dates.json'))
base_dates = [date.fromisoformat(s) for s in dates['base']]
tgt_dates  = [date.fromisoformat(s) for s in dates['tgt']]
eom = [0,31,60,91,121,152,182,213,244,274,305,335,366]
doy_of = lambda d: eom[d.month-1] + d.day

base_idx = {d: i for i, d in enumerate(base_dates)}
pool_idx = {}
for d in range(1, 367):
    if d == 60: continue
    m = next(mm for mm in range(1,13) if eom[mm-1] < d <= eom[mm])
    day = d - eom[m-1]
    idx = set()
    for y in range(1992, 2003):
        b = date(y, m, day)
        for off in range(-5, 6):
            t = b + timedelta(days=off)
            if t in base_idx: idx.add(base_idx[t])
    pool_idx[d] = np.array(sorted(idx), dtype=np.int64)
print("pool sizes: d1:", len(pool_idx[1]), "d61:", len(pool_idx[61]), "d366:", len(pool_idx[366]))

thr_mp = np.full((366,3600), np.nan)
for d in range(1, 367):
    if d == 60: continue
    thr_mp[d-1] = np.nanquantile(A_base[pool_idx[d]], 0.9, method='hazen', axis=0).ravel()
thr_mp[59] = 0.5*(thr_mp[58]+thr_mp[60])
def smooth31(a):
    out = np.zeros_like(a)
    for j in range(-15,16): out += np.roll(a, j, axis=0)
    return out/31
thr_mp_s = smooth31(thr_mp)
doy_t = np.array([doy_of(d) for d in tgt_dates])
H_mp = A_tgt >= thr_mp_s[doy_t-1].reshape(92,60,60)

thr_in = np.full((366, 3600), np.nan)
for d in range(1, 367):
    if d == 60: continue
    m = next(mm for mm in range(1,13) if eom[mm-1] < d <= eom[mm])
    day = d - eom[m-1]
    vals = []
    for y in range(1992, 2003):
        b = date(y, m, day)
        for off in range(-5, 6):
            t = b + timedelta(days=off)
            if base_dates[0] <= t <= base_dates[-1]:
                vals.append((t - base_dates[0]).days)
    thr_in[d-1] = np.nanquantile(A_base[vals], 0.9, method='hazen', axis=0).ravel()
thr_in[59] = 0.5*(thr_in[58]+thr_in[60])
thr_in_s = smooth31(thr_in)
H_in = A_tgt >= thr_in_s[doy_t-1].reshape(92,60,60)

d = ~np.isclose(thr_mp_s[doy_t-1].reshape(92,3600), thr_in_s[doy_t-1].reshape(92,3600), equal_nan=True)
print("thr diffs:", int(d.sum()), "H diffs:", int((H_mp != H_in).sum()))

import xarray as xr
mask = xr.open_dataset('/work/output/mhw_mask.nc')['mhw'].values
print("H_mp-based mask vs file: need MHW step; compare hot instead")
# The earlier failing comparison used thr_in & naive cell_mhw; redo with both
def cell_mhw(h):
    n=len(h); runs=[]; i=0
    while i<n:
        if h[i]:
            j=i
            while j+1<n and h[j+1]: j+=1
            runs.append((i,j)); i=j+1
        else: i+=1
    runs=[(a,b) for a,b in runs if b-a+1>=5]
    merged=[]
    for a,b in runs:
        if merged and a-merged[-1][1]-1<=2: merged[-1]=(merged[-1][0],b)
        else: merged.append((a,b))
    out=np.zeros(n,bool)
    for a,b in merged: out[a:b+1]=True
    return out
M = np.stack([cell_mhw(H_in[:,i,j]) for j in range(60) for i in range(60)], axis=1).reshape(92,60,60)
print("independent MHW == file mask:", bool((M == (mask>0)).all()))
diff = (M != (mask>0))
print("diff cells:", int(diff.sum()))
if diff.sum():
    t0, i0, j0 = np.where(diff)[0]
    print("first diff at t, i, j:", t0, i0, j0, tgt_dates[t0])
