import numpy as np, pickle, time
X = np.load("/tmp/X.npy")
pools = pickle.load(open("/tmp/pools.pkl","rb"))["pools"]
Nc = 3600
Xd = X.reshape(4028, Nc)

def hazen90(S, pool):
    nv = 121 - np.isnan(pool).sum(axis=0)
    j = 0.9*nv - 0.5
    jf = np.clip(np.floor(j).astype(np.int64), 0, 120)
    jc = np.minimum(jf+1, 120)
    frac = j - jf
    a = np.take_along_axis(S, jf[None,:], axis=0)[0]
    b = np.take_along_axis(S, jc[None,:], axis=0)[0]
    return np.where(nv > 0, a + frac*(b-a), np.nan), nv

t0=time.time()
thr = np.full((366, Nc), np.nan)
clim = np.full((366, Nc), np.nan)
for d in range(1, 367):
    if d == 60:
        continue
    pool = Xd[pools[d]]                     # (121, 3600)
    S = np.sort(pool, axis=0)
    q, nv = hazen90(S, pool)
    thr[d-1] = q
    clim[d-1] = np.where(nv > 0, np.nansum(pool, axis=0)/nv, np.nan)
print("pools done in", round(time.time()-t0,1), "s")

thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

def smooth31(a):
    a2 = np.concatenate([a, a, a])
    out = np.empty_like(a)
    for d in range(366):
        start = d - 15 + 366
        out[d] = a2[start:start+31].mean(axis=0)
    return out
t0=time.time()
thr_s = smooth31(thr)
clim_s = smooth31(clim)
print("smoothing done in", round(time.time()-t0,1), "s")
sea2 = np.isfinite(np.load("/tmp/target.pkl")["T"]).all(axis=0)  # placeholder, will load properly next
print("thr range:", np.nanmin(thr_s), np.nanmax(thr_s), "clim range:", np.nanmin(clim_s), np.nanmax(clim_s))
pickle.dump({"thr_s":thr_s, "clim_s":clim_s}, open("/tmp/thrclim.pkl","wb"))
print("saved /tmp/thrclim.pkl")
