import numpy as np, json
from datetime import date, timedelta
import xarray as xr

z = np.load('/work/cache/data.npz')
A_base = z['A_base'].astype(np.float64)
A_tgt  = z['A_tgt'].astype(np.float64)
dates = json.load(open('/work/cache/dates.json'))
base_dates = [date.fromisoformat(s) for s in dates['base']]
tgt_dates  = [date.fromisoformat(s) for s in dates['tgt']]
eom = [0,31,60,91,121,152,182,213,244,274,305,335,366]
doy_of = lambda d: eom[d.month-1] + d.day

sea = np.all(np.isfinite(A_tgt), axis=0)

# --- recompute thresholds with an independent, slow, explicit implementation (full 366, all cells) ---
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
                i = (t - base_dates[0]).days
                vals.append(i)
    X = A_base[vals]  # (k,60,60)
    thr[d-1] = np.nanquantile(X, 0.9, method='hazen', axis=0).ravel()
thr[59] = 0.5*(thr[58]+thr[60])
def smooth31(a):
    out = np.zeros_like(a)
    for j in range(-15,16): out += np.roll(a, j, axis=0)
    return out/31
thr_s = smooth31(thr)

print("all target-doy smoothed thr finite for sea cells:", bool(np.isfinite(thr_s[152:245, :]).reshape(92,3600)[:, sea.ravel()].all() if False else np.isfinite(thr_s[152:245]).reshape(92,3600)[:, sea.ravel()].all()))

# compare to the main pipeline's values: rerun main pipeline quickly? Instead verify hot mask from file
ds = xr.open_dataset('/work/output/mhw_mask.nc')
print(ds)
mask = ds['mhw'].values
print("mask shape/dtype:", mask.shape, mask.dtype, "time:", ds.time.values[:2], ds.time.values[-1])
print("lat/lon ranges:", float(ds.lat.min()), float(ds.lat.max()), float(ds.lon.min()), float(ds.lon.max()))

# reconstruct hot days with the independent thr and compare per-cell MHW to mask
H = (A_tgt >= thr_s[152:245].reshape(92,3600)[:, :]).reshape(92,3600)
# wait thr_s is (366,3600); target doy 153..244 -> index 152..243
doy_t = np.array([doy_of(d) for d in tgt_dates])
H = A_tgt >= thr_s[doy_t-1].reshape(92,3600)

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

M = np.zeros((92,3600), bool)
for c in range(3600): M[:,c] = cell_mhw(H[:,c])
print("independent MHW == file mask:", bool((M.reshape(92,60,60) == (mask>0)).all()))

# spot-check one cell end-to-end: cell index 0 (lat 57.84, lon 17.42)
c = 0
print("cell0 sea?", bool(sea.ravel()[c]))
print("cell0 hot days:", [ (tgt_dates[i].isoformat()) for i in np.where(H[:,c])[0] ][:20])
print("cell0 MHW days:", [(tgt_dates[i].isoformat()) for i in np.where(M[:,c])[0]][:20])
