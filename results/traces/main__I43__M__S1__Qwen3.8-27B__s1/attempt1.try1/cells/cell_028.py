import numpy as np, pickle, time, warnings
X = np.load("/tmp/X.npy")
pools = pickle.load(open("/tmp/pools.pkl","rb"))["pools"]
meta = pickle.load(open("/tmp/target.pkl","rb"))
sea = meta["sea"]
Nc = 3600
Xd = X.reshape(4028, Nc)

def hazen90(pool):
    S = np.sort(pool, axis=0)
    nv = 121 - np.isnan(pool).sum(axis=0)
    j = 0.9*nv - 0.5
    jf = np.clip(np.floor(j).astype(np.int64), 0, 120)
    jc = np.minimum(jf+1, 120)
    frac = j - jf
    a = np.take_along_axis(S, jf[None,:], axis=0)[0]
    b = np.take_along_axis(S, jc[None,:], axis=0)[0]
    return np.where(nv > 0, a + frac*(b-a), np.nan), nv

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    thr = np.full((366, Nc), np.nan)
    clim = np.full((366, Nc), np.nan)
    for d in range(1, 367):
        if d == 60:
            continue
        pool = Xd[pools[d]]
        q, nv = hazen90(pool)
        thr[d-1] = q
        clim[d-1] = np.where(nv > 0, np.nansum(pool, axis=0)/nv, np.nan)

thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

def smooth31(a):
    a2 = np.concatenate([a, a, a])
    out = np.empty_like(a)
    for d in range(366):
        start = d - 15 + 366
        out[d] = a2[start:start+31].mean(axis=0)
    return out
thr_s = smooth31(thr)
clim_s = smooth31(clim)
sea_flat = sea.reshape(Nc)
print("thr range:", np.nanmin(thr_s), np.nanmax(thr_s), "| clim range:", np.nanmin(clim_s), np.nanmax(clim_s))
print("cells with NaN thr:", int(np.isnan(thr_s).any(axis=0).sum()),
      "-> at sea cells:", int(np.isnan(thr_s).any(axis=0)[sea_flat].sum()))
print("cells with NaN clim:", int(np.isnan(clim_s).any(axis=0).sum()),
      "-> at sea cells:", int(np.isnan(clim_s).any(axis=0)[sea_flat].sum()))
pickle.dump({"thr_s":thr_s, "clim_s":clim_s, "thr_raw":thr, "clim_raw":clim}, open("/tmp/thrclim.pkl","wb"))
print("saved /tmp/thrclim.pkl")
