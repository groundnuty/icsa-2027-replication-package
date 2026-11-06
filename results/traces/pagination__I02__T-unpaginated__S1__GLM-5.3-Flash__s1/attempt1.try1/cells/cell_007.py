import numpy as np, datetime as dt, time, warnings, json, os

t_start = time.time()
z = np.load('mhw_cache.npz', allow_pickle=False)
base_data = z['base_data']   # (4028, 60, 60) float32, dates 1991-12-27..2003-01-05
tgt_data  = z['tgt_data']    # (92, 60, 60) float32, dates 2004-06-01..2004-08-31
base_t = z['base_t']; tgt_t = z['tgt_t']

EXT_START = dt.date(1991,12,27)
B0, B1 = dt.date(1992,1,1), dt.date(2002,12,31)

def doy366(d):
    cum_leap = [0,31,60,91,121,152,182,213,244,274,305,335]
    cum_norm = [0,31,59,90,120,151,181,212,243,273,304,334]
    if d.month <= 2:
        return cum_leap[d.month-1] + d.day
    leap = (d.year%4==0 and d.year%100!=0) or d.year%400==0
    return (cum_norm[d.month-1] + d.day) + (0 if leap else 1)

# sanity checks of the doy mapping
for s,(y,m,dd) in {"1 Jan":(2001,1,1),"28 Feb":(2001,2,28),"29 Feb":(2000,2,29),"1 Mar":(2001,3,1),"1 Mar leap":(2000,3,1),"31 Dec":(2001,12,31)}.items():
    print(s, "->", doy366(dt.date(y,m,dd)))

ext_days = [EXT_START + dt.timedelta(days=k) for k in range(base_data.shape[0])]
ext_doy  = np.array([doy366(d) for d in ext_days])
is_base  = np.array([B0 <= d <= B1 for d in ext_days])
bi_idx   = np.where(is_base)[0]
print("extended:", ext_days[0], ext_days[-1], "n:", len(ext_days), "baseline dates:", len(bi_idx))

# build pools: for each doy d (1..366, d!=60) list of extended-array date indices
pool_idx = [[] for _ in range(367)]
for bi in bi_idx:
    d = ext_doy[bi]
    if d == 60:
        continue
    pool_idx[d].extend(range(bi-5, bi+6))
pool_idx = [np.asarray(p, dtype=np.int64) if len(p) else None for p in pool_idx]
sizes = [len(p) if p is not None else 0 for p in pool_idx[1:]]
print("pool sizes: min", min(sizes), "max", max(sizes), "d=366 size:", sizes[365], "d=60 pool:", pool_idx[60])

NY, NX = base_data.shape[1], base_data.shape[2]
thr = np.full((366, NY, NX), np.nan)
clm = np.full((366, NY, NX), np.nan)
t0 = time.time()
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60:
            continue
        vals = base_data[pool_idx[d]].astype(np.float64)     # (n, NY, NX)
        thr[d-1] = np.nanpercentile(vals, 90, axis=0, method='hazen')
        clm[d-1] = np.nanmean(vals, axis=0)
print(f"pools+quantiles done in {time.time()-t0:.1f}s")

# day 60 = mean of days 59 and 61
thr[59] = 0.5*(thr[58] + thr[60])
clm[59] = 0.5*(clm[58] + clm[60])

# centred 31-day moving mean, wrapping mod 366
def smooth31(a):
    out = np.zeros_like(a)
    for k in range(-15, 16):
        out += np.roll(a, k, axis=0)
    return out / 31.0
thr_s = smooth31(thr)
clm_s = smooth31(clm)
print("smoothing done. elapsed", time.time()-t_start)

np.savez('clim_thr.npz', thr=thr_s, clm=clm_s)
# quick sanity print for one cell
print("sample cell thr/clim doy 200:", thr_s[199,30,30], clm_s[199,30,30], " raw:", thr[199,30,30], clm[199,30,30])
print("nan count in thr_s:", np.isnan(thr_s).sum(), "in clm_s:", np.isnan(clm_s).sum())
