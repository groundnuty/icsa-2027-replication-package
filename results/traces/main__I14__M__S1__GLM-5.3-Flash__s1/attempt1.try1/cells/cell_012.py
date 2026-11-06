import numpy as np, datetime as dt, time, warnings

z = np.load("/work/cache_sst.npz")
ext32, tgt32 = z["ext"], z["tgt"]
ext_ord, tgt_ord = z["ext_ord"], z["tgt_ord"]
ext64 = ext32.astype(np.float64)

# CORRECT doy mapping: natural day-of-year (tm_yday); non-leap years have no day 60
ext_doy = np.array([dt.date.fromordinal(int(o)).timetuple().tm_yday for o in ext_ord], dtype=np.int32)
tgt_doy = np.array([dt.date.fromordinal(int(o)).timetuple().tm_yday for o in tgt_ord], dtype=np.int32)
print("ext doy range:", ext_doy.min(), ext_doy.max(), "| tgt doys:", tgt_doy.min(), "..", tgt_doy.max())
print("2015-06-01 ->", tgt_doy[0], "| 2015-08-31 ->", tgt_doy[-1])

sea_ext = np.all(np.isfinite(ext64), axis=0)
b_start = dt.date(1992,1,1).toordinal(); b_end = dt.date(2002,12,31).toordinal()
bmask = (ext_ord >= b_start) & (ext_ord <= b_end)
print("baseline dates:", int(bmask.sum()))

thr_raw = np.full((366, 60, 60), np.nan)
clim_raw = np.full((366, 60, 60), np.nan)
pool_sizes = {}
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
        pool = ext64[m]
        pool_sizes[d] = (len(b_dates), pool.shape[0])
        thr_raw[d-1] = np.nanpercentile(pool, 90, axis=0, method="hazen")
        clim_raw[d-1] = np.nanmean(pool, axis=0)
print("pools done in %.1f s" % (time.time()-t0))
bd, pd_ = zip(*pool_sizes.values())
print("baseline dates per doy: min %d max %d | pool sizes: min %d max %d (expect 121 each)" %
      (min(bd), max(bd), min(pd_), max(pd_)))
print("thr_raw finite (sea):", bool(np.isfinite(thr_raw[:, sea_ext]).all()),
      "| clim finite (sea):", bool(np.isfinite(clim_raw[:, sea_ext]).all()))
print("land all-NaN in thr_raw:", bool(np.all(~np.isfinite(thr_raw[:, ~sea_ext]))))

thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])

def circ_smooth31(a):
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.concatenate([np.zeros((1,)+a.shape[1:]), np.cumsum(pad, axis=0)], axis=0)
    return (c[31:31+366] - c[0:366]) / 31.0

thr = circ_smooth31(thr_raw)
clim = circ_smooth31(clim_raw)
print("smoothed thr: %.3f..%.3f K | clim: %.3f..%.3f K" %
      (np.nanmin(thr), np.nanmax(thr), np.nanmin(clim), np.nanmax(clim)))
np.savez_compressed("/work/cache_thr2.npz", thr=thr, clim=clim, thr_raw=thr_raw, clim_raw=clim_raw)
print("saved /work/cache_thr2.npz")

# sample sea cell
i, j = np.argwhere(sea_ext)[1650]
print("sample cell lat %.2f lon %.2f" % (53.5+0.02*(132+i), 9.0+0.02*(436+j)))
print(" clim doy 1,60,152,200,243,300,366:", np.round(clim[[0,59,151,199,242,299,365], i, j], 3))
print(" thr  doy 1,60,152,200,243,300,366:", np.round(thr[[0,59,151,199,242,299,365], i, j], 3))
print(" thr-clim range: %.3f..%.3f" % (np.nanmin(thr-clim), np.nanmax(thr-clim)))
