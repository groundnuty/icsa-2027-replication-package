import numpy as np, json
from datetime import date, timedelta

dat = np.load('/tmp/sst_data.npz')
master = dat['master']; target = dat['target']
fs2 = np.load('/tmp/final_state.npz') if False else None
mchk = xr = None
import xarray as xr
chk = xr.open_dataset('output/mhw_mask.nc')
mask_out = chk['mhw'].values   # (92,60,60)
chk.close()

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

sea_mask = np.isfinite(target).all(axis=0)

# ---- fully independent re-derivation for two cells (list-based) ----
import random
random.seed(7)
sea_cells = np.argwhere(sea_mask)
samples = [sea_cells[0], sea_cells[1000], sea_cells[-1], sea_cells[1604]]
ok = True
for (ri, ck) in samples:
    # independent pool construction: walk calendar, collect dates within 5 of a doy-d baseline date
    ddt = None
    Tcol = target[:, ri, ck]
    for ti, t in enumerate(tgt_dates):
        dd = doyf(t.month, t.day)
        pool_dates = set()
        for b in base_all:
            if doyf(b.month, b.day) == dd:
                for off in range(-5, 6):
                    tt = b + timedelta(days=off)
                    if date(1991,12,27) <= tt <= date(2003,1,5):
                        pool_dates.add(tt)
        vals = [master[dmap[tt], ri, ck] for tt in pool_dates]
        vals = [v for v in vals if np.isfinite(v)]
        vals.sort()
        n = len(vals)
        # hazen: 0-indexed pos = (n+1)*p - 0.5, clipped
        pos = (n+1)*0.9 - 0.5
        pos = min(max(pos, 0.0), n-1)
        lo = int(pos); frac = pos - lo
        thr_raw = vals[lo] + (vals[lo+1]-vals[lo])*frac if lo+1 < n else vals[lo]
        # smoothing over doy circle (366): explicit
        s = 0.0
        for k in range(-15, 16):
            dd2 = dd + k
            while dd2 > 366: dd2 -= 366
            while dd2 < 1: dd2 += 366
            if dd2 == 60:
                # need thr(60) = mean(thr 59, thr 61)
                def thrd(d):
                    pool_dates = set()
                    for b in base_all:
                        if doyf(b.month, b.day) == d:
                            for off in range(-5, 6):
                                tt = b + timedelta(days=off)
                                if date(1991,12,27) <= tt <= date(2003,1,5):
                                    pool_dates.add(tt)
                    vals2 = sorted(v for v in (master[dmap[tt], ri, ck] for tt in pool_dates) if np.isfinite(v))
                    m2 = len(vals2)
                    p2 = min(max((m2+1)*0.9-0.5, 0.0), m2-1)
                    l2 = int(p2); f2 = p2 - l2
                    return vals2[l2] + (vals2[l2+1]-vals2[l2])*f2 if l2+1 < m2 else vals2[l2]
                tv = 0.5*(thrd(59) + thrd(61))
            else:
                pool_dates = set()
                for b in base_all:
                    if doyf(b.month, b.day) == dd2:
                        for off in range(-5, 6):
                            tt = b + timedelta(days=off)
                            if date(1991,12,27) <= tt <= date(2003,1,5):
                                pool_dates.add(tt)
                vals2 = sorted(v for v in (master[dmap[tt], ri, ck] for tt in pool_dates) if np.isfinite(v))
                m2 = len(vals2)
                p2 = min(max((m2+1)*0.9-0.5, 0.0), m2-1)
                l2 = int(p2); f2 = p2 - l2
                tv = vals2[l2] + (vals2[l2+1]-vals2[l2])*f2 if l2+1 < m2 else vals2[l2]
            s += tv
        thr_s = s/31.0
        # compare with pipeline mask for this cell/day
        hot_ind = bool(Tcol[ti] >= thr_s - 1e-12)
        print("cell(%d,%d) %s: SST=%.4f thr_smooth=%.4f hot_indep=%s" % (ri, ck, t, Tcol[ti], thr_s, hot_ind), end="")
        # pipeline hot recompute below; just store
    print()
print("independent trace done (spot values above)")
