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
sea = np.all(np.isfinite(A_tgt), axis=0)

thr = np.full((366, 3600), np.nan)
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
    X = A_base[vals]
    thr[d-1] = np.nanquantile(X, 0.9, method='hazen', axis=0).ravel()
thr[59] = 0.5*(thr[58]+thr[60])
def smooth31(a):
    out = np.zeros_like(a)
    for j in range(-15,16): out += np.roll(a, j, axis=0)
    return out/31
thr_s = smooth31(thr)
doy_t = np.array([doy_of(d) for d in tgt_dates])
print("doy_t range:", doy_t.min(), doy_t.max())

# NaN check: only land cells?
bad = ~np.isfinite(thr_s[doy_t-1].reshape(92,3600)).all(axis=0)
print("cells w/ any NaN smoothed thr in target:", int(bad.sum()), "of which land:", int((bad & ~sea.ravel()).sum()))

H = A_tgt >= thr_s[doy_t-1].reshape(92,3600)

ds = xr.open_dataset('/work/output/mhw_mask.nc')
print(ds)
mask = ds['mhw'].values
print("mask dtype:", mask.dtype, "shape:", mask.shape)

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

M = np.stack([cell_mhw(H[:,c]) for c in range(3600)], axis=1)
print("independent MHW == file mask:", bool((M.reshape(92,60,60) == (mask>0)).all()))

# active days & events from independent calc
active = M.any(axis=1)
ev=[]; i=0
while i<92:
    if active[i]:
        j=i
        while j+1<92 and active[j+1]: j+=1
        ev.append((tgt_dates[i].isoformat(), tgt_dates[j].isoformat())); i=j+1
    else: i+=1
print("independent events:", ev)

# spot-check cell 0
c=0
print("cell0 sea:", bool(sea.ravel()[c]))
print("cell0 hot:", [tgt_dates[i].isoformat() for i in np.where(H[:,c])[0]])
print("cell0 MHW:", [tgt_dates[i].isoformat() for i in np.where(M[:,c])[0]])
# threshold values for cell0 around the event
print("cell0 SST 2007-06-05..06-16 (K):", A_tgt[4:16, 0, 0].round(3))
print("cell0 thr same days:", thr_s[doy_t[4:16]-1, 0].round(3))
