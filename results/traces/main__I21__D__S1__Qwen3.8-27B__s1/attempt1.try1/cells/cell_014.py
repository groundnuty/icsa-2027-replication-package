import numpy as np, datetime, time
t0 = time.time()
z = np.load('/work/region.npz')
base_dates = [datetime.date.fromisoformat(s) for s in z['base_dates']]
base_sst = z['base_sst']
n = base_sst.shape[0]

doy = np.array([d.timetuple().tm_yday for d in base_dates])
b0, b1 = 5, n-6
is_anchor = np.zeros(n, bool); is_anchor[b0:b1+1] = True

NC = base_sst.shape[1]*base_sst.shape[2]
flat = base_sst.reshape(n, NC)   # (4028, 3600)

raw_thresh = np.full((366, NC), np.nan); raw_clim = np.full((366, NC), np.nan)
bad = 0
for d in range(1, 367):
    if d == 60:
        continue
    centers = np.where(is_anchor & (doy == d))[0]
    assert len(centers) == 11, (d, len(centers))
    idx = np.concatenate([np.arange(max(c-5,0), min(c+6,n)) for c in centers])
    assert len(idx) == 121, (d, len(idx))
    pool = flat[idx, :].T         # (3600, 121)
    with np.errstate(invalid='ignore'):
        raw_thresh[d] = np.nanquantile(pool, 0.90, method='hazen', axis=1)
        raw_clim[d]   = np.nanmean(pool, axis=1)
    nbad = int(np.isnan(raw_thresh[d]).sum() + np.isnan(raw_clim[d]).sum())
    bad += nbad
    if nbad: print("day", d, "NaNs:", nbad)
print("total NaN entries:", bad)

raw_thresh[60] = 0.5*(raw_thresh[59] + raw_thresh[61])
raw_clim[60]   = 0.5*(raw_clim[59]   + raw_clim[61])
print("any NaN after d60 fill:", np.isnan(raw_thresh).any(), np.isnan(raw_clim).any())

def smooth366(a):
    N = len(a)
    ext = np.concatenate([a[-15:], a, a[:15]])
    c = np.cumsum(ext)
    lo = np.arange(N)
    hi = lo + 31
    return (c[hi] - c[lo]) / 31.0

sm_thresh = smooth366(raw_thresh)
sm_clim   = smooth366(raw_clim)
for d in [1, 60, 366, 152]:
    idx = [(d-1-15 + 16*i) % 366 for i in range(31)]
    manual_t = raw_thresh[idx].mean(); manual_c = raw_clim[idx].mean()
    print(d, "ok:", abs(sm_thresh[d-1]-manual_t) < 1e-9, abs(sm_clim[d-1]-manual_c) < 1e-9)
print("elapsed:", round(time.time()-t0,1), "s")
np.savez_compressed('/work/doy_stats.npz', raw_thresh=raw_thresh, raw_clim=raw_clim,
                    sm_thresh=sm_thresh, sm_clim=sm_clim)
print("smoothed thr range:", np.nanmin(sm_thresh), np.nanmax(sm_thresh))
print("smoothed clim range:", np.nanmin(sm_clim), np.nanmax(sm_clim))
