import numpy as np, datetime as dt, time, warnings
B = np.load('work/B.npy'); T = np.load('work/T.npy')
bdays = np.load('work/bdays.npy')
bdates = [dt.date(1970,1,1)+dt.timedelta(days=int(k)) for k in bdays]

def leap(y): return y%4==0 and (y%100!=0 or y%400==0)
def doy_of(d):
    n = (d - dt.date(d.year,1,1)).days + 1
    if d.month >= 3 and not leap(d.year): n += 1
    return n
bdoy = np.array([doy_of(d) for d in bdates], dtype=np.int64)

B64 = B.astype(np.float64)
thr_raw = np.full((366, 60, 60), np.nan)   # index 0 = doy 1 ... index 365 = doy 366
clim_raw = np.full((366, 60, 60), np.nan)
pool_sizes = np.zeros(366, dtype=np.int64)

t0 = time.time()
for d in range(1, 367):
    if d == 60: 
        continue
    # dates within +-5 calendar days of any baseline date with doy == dd
    mask = np.zeros(len(bdates), dtype=bool)
    for off in range(-5, 6):
        mask |= (bdoy == d + off)
    pool_sizes[d-1] = mask.sum()
    pool = B64[mask]           # (nd, 60, 60) float64
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        thr_raw[d-1] = np.nanpercentile(pool, 90, axis=0, method='hazen')
        clim_raw[d-1] = np.nanmean(pool, axis=0)
print("pool loop time: %.1f s" % (time.time()-t0))
print("pool sizes: min", pool_sizes[pool_sizes>0].min(), "max", pool_sizes.max(), "| doy60 size:", pool_sizes[59])
print("thr_raw finite frac:", np.isfinite(thr_raw).mean(), "| clim_raw finite frac:", np.isfinite(clim_raw).mean())

# day 60 fill: mean of days 59 and 61
thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])
print("after day60 fill: thr finite frac:", np.isfinite(thr_raw).mean(), "| clim finite frac:", np.isfinite(clim_raw).mean())

# sea cells: finite SST on every target day
finT = np.isfinite(T).all(axis=0)
sea = finT
print("sea cells:", sea.sum())
# do any sea cells have NaN in raw threshold/clim?
print("sea cells with NaN thr_raw:", np.sum(sea & ~np.isfinite(thr_raw).all(axis=0)))
print("sea cells with NaN clim_raw:", np.sum(sea & ~np.isfinite(clim_raw).all(axis=0)))
# any sea cell with a NaN anywhere in baseline (missing baseline data)?
print("sea cells with any NaN in baseline B64:", np.sum(sea & ~np.isfinite(B64).all(axis=0)))
np.save('work/thr_raw.npy', thr_raw); np.save('work/clim_raw.npy', clim_raw)
print("saved raw arrays.")
