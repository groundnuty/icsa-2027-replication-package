import numpy as np
from datetime import date, timedelta
import xarray as xr

dat = np.load('/tmp/sst_data.npz')
master = dat['master']; target = dat['target']
chk = xr.open_dataset('output/mhw_mask.nc'); mask_out = chk['mhw'].values; chk.close()

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

def hazen_p90(vals):
    v = sorted(vals); n = len(v)
    pos = min(max((n+1)*0.9 - 0.5, 0.0), n-1)
    lo = int(pos); site_g = pos-lo
    return v[lo] + (v[lo+1]-v[lo])*site_g if lo+1 < n else v[lo]

# pipeline threshold recompute (vectorized, as in final pipeline)
sea_mask = np.isfinite(target).all(axis=0)
sea_cells = np.argwhere(sea_mask)
n_sea = len(sea_cells)
M = np.empty((4028, n_sea), np.float64)
T = np.empty((92, n_sea), np.float64)
for j, (i, k) in enumerate(sea_cells):
    M[:, j] = master[:, i, k]; T[:, j] = target[:, i, k]
import warnings
mord  = np.array([x.toordinal() for x in base_dates])
bords = np.array([x.toordinal() for x in base_all])
bdoy  = np.array([doyf(x.month, x.day) for x in base_all])
thr = np.full((366, n_sea), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=RuntimeWarning)
    for dd in range(1, 367):
        if dd == 60: continue
        b = bords[bdoy == dd]
        mask = np.zeros(4028, dtype=bool)
        for bo in b: mask |= (mord >= bo-5) & (mord <= bo+5)
        blk = M[np.where(mask)[0], :]
        thr[dd-1, :] = np.nanquantile(blk, 0.9, axis=0, method="hazen")
thr[59, :] = 0.5*(thr[58, :] + thr[60, :])
def smooth366(a):
    s = np.zeros_like(a)
    for k in range(-15, 16): s += np.roll(a, -k, axis=0)
    return s / 31.0
thrs = smooth366(thr)
tdoy = np.array([doyf(x.month, x.day) for x in tgt_dates])

# day index of 2021-06-20..22
for di, dt in [(19, "2021-06-20"), (20, "2021-06-21"), (21, "2021-06-22")]:
    assert tgt_dates[di].isoformat() == dt
    cells_on = np.where(mask_out[di] > 0)[0]
    cells_on = [tuple(np.unravel_index(c, (60,60))) for c in cells_on]
    print(dt, "pipeline MHW cells:", cells_on)
    for (ri, ck) in cells_on:
        j = int(np.where((sea_cells[:,0]==ri)&(sea_cells[:,1]==ck))[0][0])
        margin_pipe = T[di, j] - thrs[tdoy[di]-1, j]
        # independent thr for same cell/day
        dd = doyf(tgt_dates[di].month, tgt_dates[di].day)
        cache = {}
        def thrd(d, ri=ri, ck=ck):
            if d in cache: return cache[d]
            if d == 60:
                cache[d] = 0.5*(thrd(59)+thrd(61)); return cache[d]
            vals = [master[dmap[tt], ri, ck] for tt in pool_dates_for(d) if np.isfinite(master[dmap[tt], ri, ck])]
            cache[d] = hazen_p90(vals); return cache[d]
        s = sum(thrd((dd+k-1 if False else dd+k)) for k in range(-15,16))
        # careful with wrap:
        s = 0.0
        for k in range(-15, 16):
            d2 = dd + k
            while d2 > 366: d2 -= 366
            while d2 < 1: d2 += 366
            s += thrd(d2)
        thr_ind = s/31.0
        margin_ind = T[di, j] - thr_ind
        print("  cell(%d,%d): margin pipeline=%+.3e  independent=%+.3e  thr pipe=%.9f ind=%.9f" %
              (ri, ck, margin_pipe, margin_ind, thrs[tdoy[di]-1, j], thr_ind))
