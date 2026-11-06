import numpy as np, datetime as dt, time, json, os
print("cwd:", os.getcwd())

def doy_of(d):
    doy = (d - dt.date(d.year,1,1)).days + 1
    leap = (d.year%4==0 and (d.year%100!=0 or d.year%400==0))
    if not leap and doy >= 60:
        doy += 1
    return doy

# sanity checks of doy mapping
tests = {(2001,1,1):1,(2001,2,28):59,(2000,2,28):59,(2000,2,29):60,(2001,3,1):61,(2000,3,1):61,
         (2001,12,31):366,(2000,12,31):366,(1993,2,28):59,(1993,3,1):61}
for k,v in tests.items():
    got = doy_of(dt.date(*k))
    assert got==v, (k,got,v)
print("doy mapping OK")

bdata = np.load('/tmp/baseline.npy', mmap_mode='r')
bdates = [dt.date(1991,12,27)+dt.timedelta(days=i) for i in range(bdata.shape[0])]
bdoy = np.array([doy_of(d) for d in bdates])
print("extended range doys: first/last:", bdoy[0], bdoy[-1], bdates[0], bdates[-1])

def hazen_q90(pool):
    P=0.9
    sv = np.sort(pool, axis=0)
    n = np.isfinite(pool).sum(axis=0)
    h = (n-1)*P + 1.0
    fl = np.floor(h)
    lo = np.maximum(fl-1, 0).astype(np.int64)
    hi = (np.ceil(h)-1).astype(np.int64)
    gamma = h-fl
    r=np.arange(pool.shape[1])[:,None]; c=np.arange(pool.shape[2])[None,:]
    v_lo=sv[lo,r,c]; v_hi=sv[hi,r,c]
    diff=v_hi-v_lo
    out=v_lo+diff*gamma
    out=np.where(gamma>=0.5, v_hi-diff*(1.0-gamma), out)
    out=np.where(n>0, out, np.nan)
    return out

# validate on a pool (e.g. doy 170 mid-summer and doy 1 near boundary)
for dd in (1, 170, 366):
    donor_isel=[i for i,d in enumerate(bdates) if 1992<=d.year<=2002 and bdoy[i]==dd]
    offs=set()
    for i in donor_isel:
        for k in range(-5,6):
            j=i+k
            if 0<=j<len(bdates): offs.add(j)
    idx=np.array(sorted(offs))
    pool=np.asarray(bdata[idx]).astype(np.float64)
    q_mine=hazen_q90(pool)
    with np.errstate(all='ignore'):
        q_np=np.nanquantile(pool,0.9,axis=0,method='hazen')
    d=np.abs(q_mine-q_np); m=np.isfinite(d)
    print(f"doy {dd}: nidx={len(idx)} donors={len(donor_isel)} max|diff|={d[m].max() if m.any() else 0:.3e} nans mine/np: {(~np.isfinite(q_mine)).sum()}/{(~np.isfinite(q_np)).sum()}")
    # also check nanmean equivalence
    m_mean=np.nanmean(pool,axis=0)
    s=np.nansum(pool,axis=0); n=np.isfinite(pool).sum(axis=0)
    my_mean=np.where(n>0,s/np.maximum(n,1),np.nan)
    dd2=np.abs(my_mean-m_mean); mm=np.isfinite(dd2)
    print(f"   mean max|diff|={dd2[mm].max() if mm.any() else 0:.3e}")
