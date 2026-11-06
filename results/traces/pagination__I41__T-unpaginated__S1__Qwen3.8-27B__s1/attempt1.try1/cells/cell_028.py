import numpy as np, warnings
from datetime import date, timedelta
import xarray as xr

dat = np.load('/tmp/sst_data.npz')
master = dat['master']; target = dat['target']
chk = xr.open_dataset('output/mhw_mask.nc'); mask_out = chk['mhw'].values; t_out = chk['time'].values; chk.close()

def daterange(a,b):
    o=[]
    while a<=b: o.append(a); a+=timedelta(days=1)
    return o
base_dates = daterange(date(1991,12,27), date(2003,1,5))
tgt_dates  = daterange(date(2021,6,1), date(2021,8,31))
base_all   = daterange(date(1992,1,1), date(2002,12,31))
dmap = {x: i for i, x in enumerate(base_dates)}
mdays=[31,29,31,30,31,30,31,31,30,31,30,31]; cum=[0]
for m in mdays: cum.append(cum[-1]+m)
doyf = lambda m,dd: cum[m-1]+dd

def pool_dates_for(dd):
    s = set()
    for b in base_all:
        if doyf(b.month, b.day) == dd:
            for off in range(-5, 6):
                tt = b + timedelta(days=off)
                if date(1991,12,27) <= tt <= date(2003,1,5):
                    s.add(tt)
    return s

def hazen_np(vals):
    v = np.sort(np.asarray(vals, dtype=np.float64)); n = len(v)
    h0 = min(max(n*0.9 - 0.5, 0.0), n-1)
    lo = int(h0); site_g = h0 - lo
    return v[lo] + (v[lo+1]-v[lo])*site_g if lo+1 < n else v[lo]

sea_mask = np.isfinite(target).all(axis=0)
sea_cells = np.argwhere(sea_mask)

def indep_cell_mask(ri, ck):
    Tcol = target[:, ri, ck]
    cache = {}
    def thrd(d):
        if d in cache: return cache[d]
        if d == 60:
            cache[d] = 0.5*(thrd(59)+thrd(61)); return cache[d]
        vals = [master[dmap[tt], ri, ck] for tt in pool_dates_for(d) if np.isfinite(master[dmap[tt], ri, ck])]
        cache[d] = hazen_np(vals); return cache[d]
    hot = []
    for ti, t in enumerate(tgt_dates):
        dd = doyf(t.month, t.day)
        s = 0.0
        for k in range(-15, 16):
            d2 = dd + k
            while d2 > 366: d2 -= 366
            while d2 < 1: d2 += 366
            s += thrd(d2)
        hot.append(bool(Tcol[ti] >= s/31.0))
    runs = []
    i = 0
    while i < 92:
        if hot[i]:
            j = i
            while j+1 < 92 and hot[j+1]: j += 1
            runs.append([i, j]); i = j+1
        else:
            i += 1
    runs = [r for r in runs if r[1]-r[0]+1 >= 5]
    merged = []
    for s,e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s,e])
    m = np.zeros(92, dtype=np.uint8)
    for s,e in merged: m[s:e+1] = 1
    return m, merged, hot

tot = 0; bad = []
marg_min = 1e9
for (ri, ck) in sea_cells:
    m, merged, hot = indep_cell_mask(ri, ck)
    d = int((m != mask_out[:, ri, ck]).sum())
    tot += d
    if d and len(bad) < 8: bad.append((int(ri), int(ck), d))
print("corrected independent re-derivation: mismatched cell-days:", tot, "of", 92*len(sea_cells), "bad:", bad)

# trace cells active on 06-20 in pipeline
for (ri, ck) in [(0,0), (0,3)]:
    m, merged, hot = indep_cell_mask(ri, ck)
    print("cell(%d,%d) merged MHWs (0-based day idx):" % (ri, ck), merged)
    print("   hot days:", [i for i,h in enumerate(hot) if h])
    print("   mask==pipeline:", bool((m == mask_out[:, ri, ck]).all()))

# borderline margins in pipeline
n_sea = len(sea_cells)
M = np.empty((4028, n_sea), np.float64); T = np.empty((92, n_sea), np.float64)
for j, (i, k) in enumerate(sea_cells):
    M[:, j] = master[:, i, k]; T[:, j] = target[:, i, k]
mord  = np.array([x.toordinal() for x in base_dates])
bords = np.array([x.toordinal() for x in base_all])
bdoy  = np.array([doyf(x.month, x.day) for x in base_all])
thr = np.full((366, n_sea), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=RuntimeWarning)
    for dd in range(1, 367):
        if dd == 60: continue
        b = bords[bdoy == dd]; mask = np.zeros(4028, dtype=bool)
        for bo in b: mask |= (mord >= bo-5) & (mord <= bo+5)
        thr[dd-1, :] = np.nanquantile(M[np.where(mask)[0], :], 0.9, axis=0, method="hazen")
thr[59, :] = 0.5*(thr[58, :] + thr[60, :])
def smooth366(a):
    s = np.zeros_like(a)
    for k in range(-15, 16): s += np.roll(a, -k, axis=0)
    return s/31.0
thrs = smooth366(thr)
tdoy = np.array([doyf(x.month, x.day) for x in tgt_dates])
margin = T - thrs[tdoy-1]
for eps in (1e-6, 1e-4, 1e-3, 1e-2):
    print("cell-days with |margin| < %.0e:" % eps, int((np.abs(margin) < eps).sum()))
