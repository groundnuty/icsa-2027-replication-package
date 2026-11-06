import numpy as np, datetime as dt
thr = np.load('/work/thr.npy'); cli = np.load('/work/cli.npy'); sea = np.load('/work/sea.npy')

# 1) any NaN thresholds among sea cells?
sea_thr_nan = np.isnan(thr[sea]).any(axis=1)
sea_cli_nan = np.isnan(cli[sea]).any(axis=1)
print("sea cells with NaN thr anywhere:", int(sea_thr_nan.sum()), " cli:", int(sea_cli_nan.sum()))
if sea_thr_nan.any():
    print("  cells:", np.where(sea_thr_nan)[0][:20])

# 2) independent hazen check: replicate MATLAB quantile linear interp manually for one cell/day
import random
rng = np.random.default_rng(0)
def hazen_manual(x, p=0.9):
    x = np.sort(x); n = len(x)
    h = (n+1)*p
    j = int(np.floor(h)); g = h - j
    if j < 1: return x[0]
    if j >= n: return x[-1]
    return (1-g)*x[j-1] + g*x[j]
# rebuild pool for d=153 (2009-06-01 doy check) for cell 0... use any cell with finite pool
c = int(np.argmax(sea))  # first sea cell
md = [31,29,31,30,31,30,31,31,30,31,30,31]; cum=[0]
for x in md: cum.append(cum[-1]+x)
doy_of = lambda d: cum[d.month-1]+d.day
def md_of(doy):
    for m in range(12):
        if cum[m] < doy <= cum[m+1]: return m+1, doy-cum[m]
base_dates = []
d = dt.date(1991,12,27)
while d <= dt.date(2003,1,5): base_dates.append(d); d += dt.timedelta(days=1)
base_idx = {x:i for i,x in enumerate(base_dates)}
base_arr = np.empty((4028, 3600)); 
import glob
for i, dd in enumerate(base_dates):
    base_arr[i] = np.load(f"/work/region/{dd:%Y%m%d}.npy").ravel()
for d in (153, 1):
    m, day = md_of(d)
    s=set()
    for y in range(1992,2003):
        B = dt.date(y,m,day)
        for k in range(-5,6):
            T=B+dt.timedelta(days=k)
            if dt.date(1991,12,27)<=T<=dt.date(2003,1,5): s.add(base_idx[T])
    idx = np.array(sorted(s))
    v = np.isnan(base_arr[idx, c])
    vals = base_arr[idx, c][~v]
    print(f"d={d} L={len(idx)} nan={int(v.sum())} manual90={hazen_manual(vals):.6f} numpy90={np.nanpercentile(base_arr[idx,:].T,90,axis=1,method='hazen')[c]:.6f} mean={vals.mean():.6f}")
# pool d=1 explicit dates (year 1992 part)
print("d=1 first dates:", [base_dates[i] for i in sorted(base_idx[d] for d in [dt.date(1991,12,27)+dt.timedelta(k) for k in range(11)] and [base_dates.index(dt.date(1992,1,1)) for _ in [0]])] if False else [base_dates[i] for i in [base_idx[dt.date(1991,12,27)+dt.timedelta(k)] for k in range(11)]])

# 3) smoothing wrap check
a = np.arange(366, dtype=np.float64)
sm = np.concatenate([a[-15:], a, a[:15]]).reshape(1,-1)
from numpy.lib.stride_tricks import sliding_window_view
s = sliding_window_view(sm, 31, axis=1).mean(axis=2)[0]
print("smooth at idx0:", s[0], "expect mean of [-15..15 mod 366]:", np.concatenate([a[-15:], a[:16]]).mean())
print("smooth at idx59:", s[59], "expect", a[44:75].mean())
