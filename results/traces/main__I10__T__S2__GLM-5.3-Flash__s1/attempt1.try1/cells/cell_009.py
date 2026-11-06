import numpy as np, pandas as pd, pickle, time, warnings

t0c = time.time()
with open("work/pools.pkl","rb") as fh: pools = pickle.load(fh)
base = np.concatenate([np.load(f"work/base_{s}.npy") for s in range(3647, 7675, 500)], axis=0).astype(np.float64)
tgt  = np.load("work/tgt.npy").astype(np.float64)
sea = np.all(np.isfinite(tgt), axis=0)

thr = np.full((60,60,366), np.nan, dtype=np.float64)
clm = np.full((60,60,366), np.nan, dtype=np.float64)
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=RuntimeWarning)
    for dd in range(1, 367):
        if dd == 60: continue
        vals = base[np.asarray(pools[dd])]
        thr[:,:,dd-1] = np.nanquantile(vals, 0.90, axis=0, method='hazen')
        clm[:,:,dd-1] = np.nanmean(vals, axis=0)
thr[:,:,59] = 0.5*(thr[:,:,58] + thr[:,:,60])
clm[:,:,59] = 0.5*(clm[:,:,58] + clm[:,:,60])

def smooth31_circ(a):
    p = np.concatenate([a[..., -15:], a, a[..., :15]], axis=-1)
    w = np.lib.stride_tricks.sliding_window_view(p, 31, axis=-1)
    return w.mean(axis=-1)

thr_s = smooth31_circ(thr); clm_s = smooth31_circ(clm)
m = np.r_[np.arange(351,366), np.arange(0,16)]
print("circ check thr max|diff|:", float(np.nanmax(np.abs(thr_s[:,:,0] - thr[:,:,m].mean(axis=-1)))))
print("circ check clm max|diff|:", float(np.nanmax(np.abs(clm_s[:,:,0] - clm[:,:,m].mean(axis=-1)))))
print("day60 fill check thr: max|thr_s59 - mean(thr_s58,thr_s60)|:",
      float(np.nanmax(np.abs(thr_s[:,:,59] - 0.5*(thr_s[:,:,58]+thr_s[:,:,60])))))
print("thr_s sample (sea, doy200):", float(thr_s[30,30,199]), " clm_s:", float(clm_s[30,30,199]))
np.savez_compressed("work/clim.npz", thr=thr_s, clm=clm_s, sea=sea, tgt=tgt)
print("saved; total %.1fs" % (time.time()-t0c))
