import numpy as np, json, datetime as dt

OUT="/tmp/mhw"
ext = np.load(f"{OUT}/ext.npy").reshape(4028, 3600)
dates = json.load(open(f"{OUT}/dates.json"))
ext_dates = [dt.date.fromisoformat(s) for s in dates["ext_dates"]]
MS = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
doy = lambda d: MS[d.month-1]+d.day
base_dates = ext_dates[5:5+4018]
D_base = np.array([doy(b) for b in base_dates])
G = np.arange(4018)[:,None] + np.arange(11)[None,:]

def vec_thr_clim(c, d):
    rows = np.flatnonzero(D_base == d)
    mask = np.zeros(4028, bool)
    mask[G[rows].ravel()] = True
    idx = np.flatnonzero(mask)
    pool = ext[idx, c]
    pool = pool[np.isfinite(pool)]
    th = np.nanquantile(pool, 0.9, method="hazen")
    cl = np.nanmean(pool)
    return th, cl, len(pool)

def hazen90(x):
    x = np.sort(x); n=len(x); h=(n+1)*0.9; j=int(np.floor(h)); g=h-j
    a = x[j-1] if j-1>=0 else x[0]; b = x[j] if j<n else x[n-1]
    return a + g*(b-a)

def naive_pool(c,d):
    vals=[]
    for b in base_dates:
        if doy(b)!=d: continue
        for k in range(-5,6):
            t=b+dt.timedelta(days=k)
            i = ext_dates.index(t) if t in ext_idx else -1
            if i>=0:
                v=ext[i,c]
                if np.isfinite(v): vals.append(v)
    return np.array(vals)
ext_idx = {d:i for i,d in enumerate(ext_dates)}

# recompute full unsmoothed arrays for cells 12,13,14 (all 366 doys, incl 60 rule) and compare
cells=[12,13,14]
import time; t0=time.time()
unsm = {c: (np.full(366,np.nan), np.full(366,np.nan)) for c in cells}
for d in range(1,367):
    if d==60: continue
    for c in cells:
        th,cl,_ = vec_thr_clim(c,d)
        unsm[c][0][d-1]=th; unsm[c][1][d-1]=cl
for c in cells:
    unsm[c][0][59]=(unsm[c][0][58]+unsm[c][0][60])/2
    unsm[c][1][59]=(unsm[c][1][58]+unsm[c][1][60])/2
print("recomputed unsmoothed in", round(time.time()-t0,1),"s")

def smooth31col(a):
    b=np.concatenate([a,a]); S=np.concatenate([np.zeros(1), np.nancumsum(b)])
    return np.array([(S[((d-15)%366)+31]-S[(d-15)%366])/31 for d in range(366)])

# compare vectorized-smoothed saved arrays vs unsmoothed-smoothed here
for c in cells:
    ts = smooth31col(unsm[c][0])
    cs = smooth31col(unsm[c][1])
    # saved smoothed for this cell (from full-array smoothing; smoothing is per-column so identical)
    ok_t = np.allclose(ts, np.load(f"{OUT}/thr_s.npy")[:,c], atol=0, rtol=0, equal_nan=True)
    ok_c = np.allclose(cs, np.load(f"{OUT}/clim_s.npy")[:,c], atol=0, rtol=0, equal_nan=True)
    print("cell",c,"smoothed matches saved:", ok_t, ok_c)
    # naive check on a few doys
    for d in (153,168,183,59,60,61):
        nv = naive_pool(c,d)
        nvr = hazen90(nv) if len(nv) else np.nan
        nvc = nv.mean() if len(nv) else np.nan
        if d==60:
            nvr = (hazen90(naive_pool(c,59))+hazen90(naive_pool(c,61)))/2
            nvc = (naive_pool(c,59).mean()+naive_pool(c,61).mean())/2
        nts = np.mean([unsm[c][0][(d-1+dd-15)%366] for dd in range(31)])
        ncs = np.mean([unsm[c][1][(d-1+dd-15)%366] for dd in range(31)])
        print(f"  cell{c} doy{d}: vec_thr {unsm[c][0][d-1]:.9f} naive {nvr:.9f} | "
              f"smoothed vec {ts[d-1]:.9f} naive {nts:.9f} | clim naive {nvc:.9f} climsmooth naive {ncs:.9f}")
print("time", round(time.time()-t0,1))
