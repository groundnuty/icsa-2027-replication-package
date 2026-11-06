import numpy as np, datetime as dt

z = np.load("/work/cache_sst.npz"); ext32, tgt32 = z["ext"], z["tgt"]
z2 = np.load("/work/cache_thr2.npz"); thr, clim, thr_raw, clim_raw = z2["thr"], z2["clim"], z2["thr_raw"], z2["clim_raw"]
ext_ord = z["ext_ord"]
ext64 = ext32.astype(np.float64)
ext_doy = np.array([dt.date.fromordinal(int(o)).timetuple().tm_yday for o in ext_ord], dtype=np.int32)
b_start = dt.date(1992,1,1).toordinal(); b_end = dt.date(2002,12,31).toordinal()
bmask = (ext_ord >= b_start) & (ext_ord <= b_end)
sea = np.all(np.isfinite(tgt32.astype(np.float64)), axis=0)

# day-60 fill check, restricted to sea cells (land is NaN by design)
ok60 = (np.allclose(thr_raw[59, sea], 0.5*(thr_raw[58, sea]+thr_raw[60, sea]), rtol=0, atol=0) and
        np.allclose(clim_raw[59, sea], 0.5*(clim_raw[58, sea]+clim_raw[60, sea]), rtol=0, atol=0))
print("day60 == mean(day59,day61) on sea cells (exact):", ok60)

# naive direct-sum smoothing (sum the 31 values in index order, no cumsum)
def circ_smooth31_naive(a):   # a: (366, ...)
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)   # (396, ...)
    windows = np.lib.stride_tricks.sliding_window_view(pad, 31, axis=0)[:366]  # (366, ..., 31)
    return np.sum(windows, axis=-1) / 31.0
thr_n = circ_smooth31_naive(thr_raw)
clim_n = circ_smooth31_naive(clim_raw)
print("max |cumsum-smooth - naive-sum-smooth| thr: %.3e K, clim: %.3e K" %
      (np.nanmax(np.abs(thr-thr_n)), np.nanmax(np.abs(clim-clim_n))))

# closest hot-day margin in the target period: min |SST - thr| over all sea cell-days
tgt64 = tgt32.astype(np.float64)
tgt_doy = np.array([dt.date.fromordinal(int(o)).timetuple().tm_yday for o in z["tgt_ord"]], dtype=np.int32)
thr_t = thr[tgt_doy-1]                       # (92,60,60)
diff = np.abs(tgt64 - thr_t)[:, sea]
finite = np.isfinite(diff)
print("min |SST-thr| over target sea cell-days: %.6e K" % diff[finite].min())
print("count of cell-days within 1e-9 of threshold:", int((diff[finite] < 1e-9).sum()))
# and with the naive-smoothed threshold
thr_tn = thr_n[tgt_doy-1]
diffn = np.abs(tgt64 - thr_tn)[:, sea]
print("min |SST-thr_naive|: %.6e K" % diffn[np.isfinite(diffn)].min())
# sign agreement of comparisons
h1 = (tgt64 >= thr_t)[:, sea]; h2 = (tgt64 >= thr_tn)[:, sea]
print("hot-day masks identical (cumsum vs naive smoothing):", bool(np.array_equal(h1[finite], h2[finite])))
