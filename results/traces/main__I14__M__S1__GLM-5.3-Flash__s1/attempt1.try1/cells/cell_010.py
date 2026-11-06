import numpy as np, datetime as dt, time, warnings

z = np.load("/work/cache_sst.npz")
ext32, tgt32 = z["ext"], z["tgt"]
ext_ord, tgt_ord = z["ext_ord"], z["tgt_ord"]
ext64 = ext32.astype(np.float64)
print("ext:", ext64.shape, "tgt:", tgt32.shape, tgt32.dtype)

CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def leap_doy_ord(o):
    d = dt.date.fromordinal(int(o))
    return CUM[d.month-1] + d.day

ext_doy = np.array([leap_doy_ord(o) for o in ext_ord], dtype=np.int32)
tgt_doy = np.array([leap_doy_ord(o) for o in tgt_ord], dtype=np.int32)
print("ext doy range:", ext_doy.min(), ext_doy.max(), "| tgt doys:", tgt_doy.min(), "..", tgt_doy.max())

# land mask checks
sea_tgt = np.all(np.isfinite(tgt32), axis=0)
sea_ext = np.all(np.isfinite(ext64), axis=0)
print("sea cells (target):", int(sea_tgt.sum()), "| cells finite ALL baseline ext days:", int(sea_ext.sum()),
      "| identical:", np.array_equal(sea_tgt, sea_ext))
print("non-sea cells all-NaN on every ext day:", bool(np.all(~np.isfinite(ext64[:, ~sea_ext]))))

# baseline ordinal window
b_start = dt.date(1992,1,1).toordinal(); b_end = dt.date(2002,12,31).toordinal()
bmask = (ext_ord >= b_start) & (ext_ord <= b_end)
print("baseline dates:", int(bmask.sum()), "(expect 4018 = 11 years incl 3x366)")

# --- pools, raw threshold & climatology ---
thr_raw = np.full((366, 60, 60), np.nan)
clim_raw = np.full((366, 60, 60), np.nan)
pool_sizes = []
t0 = time.time()
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=RuntimeWarning)
    for d in range(1, 367):
        if d == 60:
            continue
        b_dates = ext_ord[bmask & (ext_doy == d)]
        P = set()
        for b in b_dates:
            P.update(range(int(b)-5, int(b)+6))
        P = np.fromiter(P, dtype=np.int64)
        m = np.isin(ext_ord, P)
        pool = ext64[m]                      # (nd, 60, 60) float64
        pool_sizes.append((d, len(b_dates), pool.shape[0]))
        thr_raw[d-1] = np.nanpercentile(pool, 90, axis=0, method="hazen")
        clim_raw[d-1] = np.nanmean(pool, axis=0)
print("pools done in %.1f s" % (time.time()-t0))
ps = np.array([p[2] for p in pool_sizes])
print("pool sizes: min %d max %d  (d=366 pool: %d, d=1 pool: %d)" % (ps.min(), ps.max(),
      dict((p[0],p[2]) for p in pool_sizes)[366], dict((p[0],p[2]) for p in pool_sizes)[1]))
print("thr_raw finite everywhere (sea):", bool(np.isfinite(thr_raw[:, sea_ext]).all()),
      "| clim finite (sea):", bool(np.isfinite(clim_raw[:, sea_ext]).all()))

# day 60 = mean of days 59 and 61 (raw, before smoothing)
thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])
print("day60 fill done")

# --- circular 31-day moving mean, mod 366 ---
def circ_smooth31(a):  # a: (366, ...) along axis 0
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.concatenate([np.zeros((1,)+a.shape[1:]), np.cumsum(pad, axis=0)], axis=0)
    return (c[31:31+366] - c[0:366]) / 31.0

thr = circ_smooth31(thr_raw)
clim = circ_smooth31(clim_raw)
print("smoothed: thr range %.3f..%.3f K | clim range %.3f..%.3f K" %
      (np.nanmin(thr), np.nanmax(thr), np.nanmin(clim), np.nanmax(clim)))
np.savez_compressed("/work/cache_thr.npz", thr=thr, clim=clim, thr_raw=thr_raw, clim_raw=clim_raw)
print("saved /work/cache_thr.npz")

# sanity: climatology for one sea cell through the year (every 30 days)
cell = np.argwhere(sea_ext)[len(np.argwhere(sea_ext))//2]
r, c = cell
print("sample sea cell (lat %.2f, lon %.2f):" % (53.5+0.02*(132+r), 9.0+0.02*(436+c)))
print("  clim doy 1,60,120,180,240,300,366:", np.round(clim[[0,59,119,179,239,299,365], r, c], 3))
print("  thr  doy 1,60,120,180,240,300,366:", np.round(thr[[0,59,119,179,239,299,365], r, c], 3))
print("  thr-clim min/max: %.3f / %.3f" % (np.nanmin(thr-clim), np.nanmax(thr-clim)))
