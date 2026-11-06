import numpy as np, datetime as dt, time, os

bdata = np.load('/tmp/baseline.npy', mmap_mode='r')
bdates = [dt.date(1991,12,27)+dt.timedelta(days=i) for i in range(bdata.shape[0])]

def doy_of(d):
    doy = (d - dt.date(d.year,1,1)).days + 1
    leap = (d.year%4==0 and (d.year%100!=0 or d.year%400==0))
    if not leap and doy >= 60:
        doy += 1
    return doy

bdoy = np.array([doy_of(d) for d in bdates])
in_baseline = np.array([1992 <= d.year <= 2002 for d in bdates])
N = len(bdates)

def hazen_q90(pool, P=0.9):
    sv = np.sort(pool, axis=0)
    n = np.isfinite(pool).sum(axis=0)
    pos0 = n*P - 0.5
    lo0 = np.floor(pos0); hi0 = np.ceil(pos0)
    gamma = pos0 - lo0
    nclip = np.maximum(n-1, 0)
    lo0 = np.minimum(np.clip(lo0,0,None), nclip).astype(np.int64)
    hi0 = np.minimum(np.clip(hi0,0,None), nclip).astype(np.int64)
    r=np.arange(pool.shape[1])[:,None]; c=np.arange(pool.shape[2])[None,:]
    v_lo=sv[lo0,r,c]; v_hi=sv[hi0,r,c]
    out = v_lo + (v_hi-v_lo)*gamma
    out = np.where(gamma>=0.5, v_hi-(v_hi-v_lo)*(1.0-gamma), out)
    return np.where(n>0, out, np.nan)

def circ_movmean31(a):
    # a: (366, ...) float64, axis 0 is day-of-year (index 0 -> doy 1)
    P = 366
    out = np.empty_like(a)
    idx = (np.arange(P)[:,None] + np.arange(-15,16)[None,:]) % P
    w = a[idx]              # (366, 31, ...)
    return w.mean(axis=1)

t0=time.time()
thr_raw = np.full((366,60,60), np.nan)
clim_raw = np.full((366,60,60), np.nan)
pool_sizes = {}
for d in range(1,367):
    if d==60: continue
    donor = np.flatnonzero(in_baseline & (bdoy==d))
    offs=set()
    for i in donor:
        for k in range(-5,6):
            j=i+k
            if 0<=j<N: offs.add(j)
    idx=np.fromiter(sorted(offs), dtype=np.int64)
    pool_sizes[d]=(len(donor), len(idx))
    pool=np.asarray(bdata[idx]).astype(np.float64)
    thr_raw[d-1]=hazen_q90(pool)
    fin=np.isfinite(pool)
    s=np.where(fin,pool,0.0).sum(axis=0)
    n=fin.sum(axis=0)
    with np.errstate(invalid='ignore'):
        clim_raw[d-1]=np.where(n>0, s/np.where(n>0,n,1), np.nan)
print(f"pools done in {time.time()-t0:.1f}s")

# fill day 60 (index 59) with mean of day 59 (idx 58) and day 61 (idx 60)
thr_raw[59]=0.5*(thr_raw[58]+thr_raw[60])
clim_raw[59]=0.5*(clim_raw[58]+clim_raw[60])

# circular 31-day moving mean
thr_sm=circ_movmean31(thr_raw)
clim_sm=circ_movmean31(clim_raw)
print(f"total {time.time()-t0:.1f}s")

sizes=np.array([pool_sizes[d][1] for d in range(1,367) if d!=60])
don=np.array([pool_sizes[d][0] for d in range(1,367) if d!=60])
import collections
print("pool day-counts (unique):", collections.Counter(sizes.tolist()))
print("donor counts (unique):", collections.Counter(don.tolist()))
print("thr_sm[152] (doy153, cell 40,40):", thr_sm[152,40,40], " clim:", clim_sm[152,40,40])
print("thr range sea cells:", np.nanmin(thr_sm), np.nanmax(thr_sm))
print("clim range sea cells:", np.nanmin(clim_sm), np.nanmax(clim_sm))
np.save('/tmp/thr_sm.npy', thr_sm)
np.save('/tmp/clim_sm.npy', clim_sm)
print("saved")
