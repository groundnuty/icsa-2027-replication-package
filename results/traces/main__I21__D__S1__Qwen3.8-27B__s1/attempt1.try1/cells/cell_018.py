import numpy as np, datetime, time
t0 = time.time()
z = np.load('/work/region.npz')
base_dates = [datetime.date.fromisoformat(s) for s in z['base_dates']]
tgt_dates  = [datetime.date.fromisoformat(s) for s in z['tgt_dates']]
base_sst = z['base_sst']
n = base_sst.shape[0]

# month-day -> doy mapping in a LEAP calendar (Jan1=1, Feb29=60, Dec31=366)
CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def md_doy(d):
    return CUM[d.month-1] + d.day
def md_doy_arr(ds):
    return np.array([CUM[d.month-1] + d.day for d in ds])

doy = md_doy_arr(base_dates)
doy_tgt = md_doy_arr(tgt_dates)
print("base doy[0..5]:", doy[:6], "doy[-6:]:", doy[-6:])
print("target doy range:", doy_tgt.min(), doy_tgt.max(), " (Jun1,Aug31 = 153,244 expected)")
print("n 366 anchors:", ((doy==366)).sum(), "n doy60 in window:", (doy==60).sum())

b0, b1 = 5, n-6
is_anchor = np.zeros(n, bool); is_anchor[b0:b1+1] = True

NC = base_sst.shape[1]*base_sst.shape[2]
flat = base_sst.reshape(n, NC)

raw_thresh = np.full((366, NC), np.nan); raw_clim = np.full((366, NC), np.nan)
poolidx = {}
for d in range(1, 367):
    if d == 60:
        continue
    centers = np.where(is_anchor & (doy == d))[0]
    assert len(centers) == 11, (d, len(centers))
    idx = np.concatenate([np.arange(max(c-5,0), min(c+6,n)) for c in centers])
    assert len(idx) == 121, (d, len(idx))
    poolidx[d] = idx
    pool = flat[idx, :].T
    with np.errstate(invalid='ignore'):
        raw_thresh[d] = np.nanquantile(pool, 0.90, method='hazen', axis=1)
        raw_clim[d]   = np.nanmean(pool, axis=1)
print("NaNs per day (should be 572 = 286 land cells x2):",
      int((np.isnan(raw_thresh[:60]).sum()) - 0), int((np.isnan(raw_thresh[:, :100]).sum()) - 0))
print("total NaN thr entries:", int(np.isnan(raw_thresh).sum()), "(expect 366*286 =", 366*286, ")")
print("total NaN clim entries:", int(np.isnan(raw_clim).sum()))

raw_thresh[60] = 0.5*(raw_thresh[59] + raw_thresh[61])
raw_clim[60]   = 0.5*(raw_clim[59]   + raw_clim[61])
print("any NaN after d60 fill:", np.isnan(raw_thresh).any(), np.isnan(raw_clim).any())

def smooth366(a):
    ext = np.concatenate([a[-15:], a, a[:15]])
    c = np.cumsum(ext)
    lo = np.arange(len(a)); hi = lo + 31
    return (c[hi] - c[lo]) / 31.0

sm_thresh = smooth366(raw_thresh)
sm_clim   = smooth366(raw_clim)
for d in [1, 60, 153, 244, 366]:
    idx = [(d-1-15 + 16*i) % 366 for i in range(31)]
    ok = abs(sm_thresh[d-1] - raw_thresh[idx].mean()) < 1e-9 and abs(sm_clim[d-1] - raw_clim[idx].mean()) < 1e-9
    print("smooth check d=", d, ok)
print("elapsed:", round(time.time()-t0,1), "s")
np.savez_compressed('/work/doy_stats.npz', raw_thresh=raw_thresh, raw_clim=raw_clim,
                    sm_thresh=sm_thresh, sm_clim=sm_clim,
                    target_doy=doy_tgt)
print("smoothed thr range:", np.nanmin(sm_thresh), np.nanmax(sm_thresh))
