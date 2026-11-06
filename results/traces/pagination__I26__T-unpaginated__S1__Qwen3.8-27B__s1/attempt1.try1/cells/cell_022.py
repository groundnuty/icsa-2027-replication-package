import numpy as np, json, warnings
from datetime import date, timedelta
import xarray as xr
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
thr = np.full((366,3600), np.nan)
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
    thr[d-1] = np.nanquantile(A_base[sorted(idx)], 0.9, method='hazen', axis=0).ravel()
thr[59] = 0.5*(thr[58]+thr[60])
def smooth31(a):
    out = np.zeros_like(a)
    for j in range(-15,16): out += np.roll(a, j, axis=0)
    return out/31
thr_s = smooth31(thr)
doy_t = np.array([doy_of(d) for d in tgt_dates])
H = (A_tgt >= thr_s[doy_t-1].reshape(92,60,60)).reshape(92,3600)

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

M = np.empty((92,3600), bool)
for k in range(3600):          # k = i*60 + j  (row-major)
    M[:, k] = cell_mhw(H[:, k])
mask = xr.open_dataset('/work/output/mhw_mask.nc')['mhw'].values
print("independent MHW == file mask:", bool((M.reshape(92,60,60) == (mask>0)).all()))

# also verify naive against a fully independent per-cell recompute on a random sample using different run-finding code
import random
random.seed(1)
def cell_mhw_v2(h):
    # different algorithm: use np diff
    n = len(h)
    pad = np.concatenate(([False], h, [False]))
    edges = np.diff(pad.astype(np.int8))
    starts = list(np.where(edges == 1)[0])
    ends   = list(np.where(edges == -1)[0]) - 1
    merged = []
    for a, b in zip(starts, ends):
        if b - a + 1 < 5: continue
        if merged and a - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append([a, b])
    out = np.zeros(n, bool)
    for a, b in merged: out[a:b+1] = True
    return out
ok = True
for k in random.sample(range(3600), 500):
    if not np.array_equal(cell_mhw(H[:,k]), cell_mhw_v2(H[:,k])):
        ok = False; print("alg mismatch cell", k); break
print("two independent algorithms agree on 500 random cells:", ok)

# events
active = M.any(axis=1)
ev=[]; i=0
while i<92:
    if active[i]:
        j=i
        while j+1<92 and active[j+1]: j+=1
        ev.append((tgt_dates[i].isoformat(), tgt_dates[j].isoformat())); i=j+1
    else: i+=1
print("events:", ev, "mask ones:", int(M.sum()))
