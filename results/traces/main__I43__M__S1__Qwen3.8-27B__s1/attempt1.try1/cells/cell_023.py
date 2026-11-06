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
        thr[d] = np.nanquantile(pool, 0.9, method="hazen", axis=0)
        clim[d] = np.nanmean(pool, axis=0)
print("pools done in", round(time.time()-t0,1), "s")

# day-60 fill (before smoothing)
thr[60] = 0.5*(thr[59] + thr[61])
clim[60] = 0.5*(clim[59] + clim[61])

# unweighted centred 31-day moving mean, wrap-around over 366 days
def smooth31(a):
    a2 = np.concatenate([a, a, a])              # (1098, Nc)
    # day index d (1..366) -> 0-based d-1; window d-15..d+15 mod 366 -> start (d-1-15)+366
    starts = np.arange(366) - 15 + 366          # 0-based start in a2 for each d
    out = np.empty_like(a)
    for d in range(366):
        out[d] = a2[starts[d]:starts[d]+31].mean(axis=0)
    return out
t0=time.time()
thr_s = smooth31(thr)
clim_s = smooth31(clim)
print("smoothing done in", round(time.time()-t0,1), "s")
print("thr range:", np.nanmin(thr_s), np.nanmax(thr_s), "clim range:", np.nanmin(clim_s), np.nanmax(clim_s))
print("any NaN thr at sea cells:", np.isnan(thr_s).any(axis=0)[sea].any(),
      "| any NaN clim at sea cells:", np.isnan(clim_s).any(axis=0)[sea].any())
pickle.dump({"thr_s":thr_s, "clim_s":clim_s}, open("/tmp/thrclim.pkl","wb"))
print("saved /tmp/thrclim.pkl")
