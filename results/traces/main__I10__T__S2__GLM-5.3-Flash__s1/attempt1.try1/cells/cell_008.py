import numpy as np, pandas as pd, pickle, time, warnings

t0c = time.time()
d = np.load("work/coords.npz")
t_base = pd.to_datetime(d['t_base']); t_tgt = pd.to_datetime(d['t_tgt'])
with open("work/pools.pkl","rb") as fh: pools = pickle.load(fh)

# assemble base (4028,60,60) float64 and target (92,60,60) float64
base = np.concatenate([np.load(f"work/base_{s}.npy") for s in range(3647, 7675, 500)], axis=0).astype(np.float64)
tgt  = np.load("work/tgt.npy").astype(np.float64)
print("base", base.shape, "tgt", tgt.shape)

sea = np.all(np.isfinite(tgt), axis=0)          # (60,60)
print("sea cells:", int(sea.sum()), "of", sea.size)
# NaN diagnostics in baseline for sea cells
base_nan_per_cell = (~np.isfinite(base)).sum(axis=0)   # (60,60)
print("baseline NaNs at sea cells: max per cell =", int(base_nan_per_cell[sea].max()) if sea.any() else None,
      "; cells with any NaN:", int((base_nan_per_cell[sea] > 0).sum()) if sea.any() else None)
tgt_nan_per_cell = (~np.isfinite(tgt)).sum(axis=0)
print("target NaNs at sea cells:", int(tgt_nan_per_cell[sea].sum()), " land NaN frac const:", bool(np.all((~np.isfinite(tgt)).sum(axis=0) == (~np.isfinite(base)).sum(axis=0))))

thr = np.full((60,60,366), np.nan, dtype=np.float64)
clm = np.full((60,60,366), np.nan, dtype=np.float64)
warn_opts = np.errstate(invalid='ignore')
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=RuntimeWarning)
    for dd in range(1, 367):
        if dd == 60: continue
        idx = np.asarray(pools[dd])
        vals = base[idx]                        # (n,60,60) float64
        thr[:,:,dd-1] = np.nanquantile(vals, 0.90, axis=0, method='hazen')
        clm[:,:,dd-1] = np.nanmean(vals, axis=0)
# day 60 = mean of days 59 and 61
thr[:,:,59] = 0.5*(thr[:,:,58] + thr[:,:,60])
clm[:,:,59] = 0.5*(clm[:,:,58] + clm[:,:,60])
print("raw clim/thr computed %.1fs" % (time.time()-t0c))
print("NaN cells in raw thr (land expected):", int(np.isnan(thr[:,:,100]).sum()))

def smooth31_circ(a):  # a: (...,366)
    p = np.concatenate([a[..., -15:], a, a[..., :15]], axis=-1)
    w = np.lib.stride_tricks.sliding_window_view(p, 31, axis=-1)   # (...,366,31)
    return w.mean(axis=-1)

thr_s = smooth31_circ(thr)
clm_s = smooth31_circ(clm)
print("smoothed %.1fs" % (time.time()-t0c))

# sanity: circular mean at day 1 equals mean of days 352..366 & 1..16
m = np.r_[np.arange(351,366), np.arange(0,16)]
assert np.allclose(thr_s[:,:,0], thr[:,:,m].mean(axis=-1), atol=1e-12)
print("circular smoothing check OK; thr_s[sea sample] range: %.2f..%.2f K" % (
    np.nanmin(thr_s[...,150:245][sea]), np.nanmax(thr_s[...,150:245][sea])))
np.savez_compressed("work/clim.npz", thr=thr_s, clm=clm_s, sea=sea, tgt=tgt)
print("saved clim.npz; total %.1fs" % (time.time()-t0c))
