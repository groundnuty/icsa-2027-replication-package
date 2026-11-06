import numpy as np, pickle, time
X = np.load("/tmp/X.npy")
pools = pickle.load(open("/tmp/pools.pkl","rb"))["pools"]
meta = pickle.load(open("/tmp/target.pkl","rb"))
sea = meta["sea"]
Nc = 3600
Xd = X.reshape(4028, Nc)

thr = np.full((366, Nc), np.nan)
clim = np.full((366, Nc), np.nan)
t0=time.time()
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60:
            continue
        pool = Xd[pools[d]]                      # (121, 3600)
        thr[d-1] = np.nanquantile(pool, 0.9, method="hazen", axis=0)
        clim[d-1] = np.nanmean(pool, axis=0)
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
print("thr range:", np.nanmin(thr_s), np.nanmax(thr_s), "clim range:", np.nanmin(clim_s), np.nanmax(clim_s))
print("any NaN thr at sea cells:", bool(np.isnan(thr_s).any(axis=0)[sea]),
      "| any NaN clim at sea cells:", bool(np.isnan(clim_s).any(axis=0)[sea]))
pickle.dump({"thr_s":thr_s, "clim_s":clim_s}, open("/tmp/thrclim.pkl","wb"))
print("saved /tmp/thrclim.pkl")
