import numpy as np, datetime, time
t0 = time.time()
z = np.load('/work/region.npz')
base_dates = [datetime.date.fromisoformat(s) for s in z['base_dates']]
tgt_dates  = [datetime.date.fromisoformat(s) for s in z['tgt_dates']]
base_sst = z['base_sst']
n = base_sst.shape[0]

CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def md_doy_arr(ds):
    return np.array([CUM[d.month-1] + d.day for d in ds])

doy = md_doy_arr(base_dates)
doy_tgt = md_doy_arr(tgt_dates)
b0, b1 = 5, n-6
is_anchor = np.zeros(n, bool); is_anchor[b0:b1+1] = True

NC = base_sst.shape[1]*base_sst.shape[2]
flat = base_sst.reshape(n, NC)

raw_thresh = np.full((366, NC), np.nan); raw_clim = np.full((366, NC), np.nan)
with np.errstate(invalid='ignore'):
    for d in range(1, 367):
        if d == 60:
            continue
        centers = np.where(is_anchor & (doy == d))[0]
        assert len(centers) == 11, (d, len(centers))
        idx = np.concatenate([np.arange(max(c-5,0), min(c+6,n)) for c in centers])
        assert len(idx) == 121, (d, len(idx))
        pool = flat[idx, :].T
        raw_thresh[d-1] = np.nanquantile(pool, 0.90, method='hazen', axis=1)
        raw_clim[d-1]   = np.nanmean(pool, axis=1)

print("total NaN thr entries:", int(np.isnan(raw_thresh).sum()), "(expect", 366*286, ")")
print("total NaN clim entries:", int(np.isnan(raw_clim).sum()))

raw_thresh[59] = 0.5*(raw_thresh[58] + raw_thresh[60])
raw_clim[59]   = 0.5*(raw_clim[58]   + raw_clim[60])
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
                    sm_thresh=sm_thresh, sm_clim=sm_clim, target_doy=doy_tgt)
print("smoothed thr range:", np.nanmin(sm_thresh), np.nanmax(sm_thresh))
print("smoothed clim range:", np.nanmin(sm_clim), np.nanmax(sm_clim))
