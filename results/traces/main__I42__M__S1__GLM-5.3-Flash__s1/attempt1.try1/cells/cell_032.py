import numpy as np, pickle, time

arr = np.load("/work/baseline_region_f32.npy")
data = arr.astype(np.float64)
with open("/work/pool_idx.pkl","rb") as f:
    pool_idx = pickle.load(f)

NT = 366
thr = np.full((NT, 60, 60), np.nan)
clim = np.full((NT, 60, 60), np.nan)
t0 = time.time()
for d in range(1, 367):
    if d == 60: continue
    v = data[pool_idx[d]]          # (121, 60, 60)
    clim[d-1] = np.nanmean(v, axis=0)
    s = np.sort(v, axis=0)
    nn = np.sum(~np.isnan(v), axis=0)      # per-cell valid counts
    with np.errstate(invalid="ignore"):
        h = nn * 0.9 + 0.5
    h = np.where(nn > 0, h, np.nan)
    lo_i = np.floor(h).astype(np.float64)
    frac = h - lo_i
    lo_c = np.clip(lo_i.astype(np.int64) - 1, 0, v.shape[0]-1)
    hi_c = np.clip(lo_i.astype(np.int64), 0, v.shape[0]-1)
    v_lo = np.take_along_axis(s, lo_c[None], axis=0)[0]
    v_hi = np.take_along_axis(s, hi_c[None], axis=0)[0]
    q = v_lo + frac * (v_hi - v_lo)
    thr[d-1] = np.where(nn > 0, q, np.nan)
print("compute time:", round(time.time()-t0,1), "s")

# fill day 60 with mean of days 59 and 61
with np.errstate(invalid="ignore"):
    thr[59] = (thr[58] + thr[60]) / 2.0
    clim[59] = (clim[58] + clim[60]) / 2.0
print("d60 thr:", thr[59,0,0], "d59 thr:", thr[58,0,0], "d61 thr:", thr[60,0,0])

def smooth_circ(a):
    s = np.zeros_like(a)
    for k in range(-15, 16):
        s += np.roll(a, -k, axis=0)
    return s / 31.0

thr_s = smooth_circ(thr)
clim_s = smooth_circ(clim)
land = ~np.isfinite(thr_s).all(axis=0)
print("land cells:", land.sum(), "; sea cells:", 3600 - land.sum())
# verify smoothing at a wrap point: doy 5 (index 4) should average doys 360..366,1..10 (indices 359..365, 0..9)
cell = (10,10)
vals = [thr[(4+k) % 366, cell[0], cell[1]] for k in range(-15,16)]
print("manual wrap doy5:", np.mean(vals), "smoothed:", thr_s[4, cell[0], cell[1]])
np.save("/work/thr_smooth2.npy", thr_s)
np.save("/work/clim_smooth2.npy", clim_s)
print("saved exact-baseline smoothed arrays")
