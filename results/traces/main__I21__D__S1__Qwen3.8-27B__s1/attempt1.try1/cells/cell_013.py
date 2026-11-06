import numpy as np, datetime, time
t0 = time.time()
z = np.load('/work/region.npz')
base_dates = [datetime.date.fromisoformat(s) for s in z['base_dates']]
base_sst = z['base_sst']          # (4028, 60, 60) float64
n = base_sst.shape[0]

doy = np.array([d.timetuple().tm_yday for d in base_dates])   # 1..366, Feb29->60
print("doy[0..10]:", doy[:11], "doy[-11:]:", doy[-11:])
b0 = 5    # index of 1992-01-01
b1 = n-6  # index of 2002-12-31
print("anchor first:", base_dates[b0], "anchor last:", base_dates[b1])
is_anchor = np.zeros(n, bool); is_anchor[b0:b1+1] = True

NC = base_sst.shape[1]*base_sst.shape[2]
flat = base_sst.reshape(n, NC)   # (4028, 3600)

raw_thresh = np.empty((366, NC)); raw_clim = np.empty((366, NC))
raw_thresh[:] = np.nan; raw_clim[:] = np.nan

for d in range(1, 367):
    if d == 60:
        continue
    centers = np.where(is_anchor & (doy == d))[0]
    assert len(centers) == 11, (d, len(centers))
    idx = np.concatenate([np.arange(max(c-5,0), min(c+6,n)) for c in centers])
    assert len(idx) == 121, (d, len(idx))
    pool = flat[:, idx]                       # (4028, 3600) -> (121, 3600)
    pool = pool.T                             # (3600, 121)
    with np.errstate(invalid='ignore'):
        raw_thresh[d] = np.nanquantile(pool, 0.90, method='hazen', axis=1)
        raw_clim[d]   = np.nanmean(pool, axis=1)
    print(d, "nan cells thr/clim:", np.isnan(raw_thresh[d]).sum(), np.isnan(raw_clim[d]).sum(), end="  |  ")
    if d % 8 == 0: print()
print()

# day 60 = mean of 59 and 61
raw_thresh[60] = 0.5*(raw_thresh[59] + raw_thresh[61])
raw_clim[60]   = 0.5*(raw_clim[59]   + raw_clim[61])
print("any NaN after d60 fill:", np.isnan(raw_thresh).any(), np.isnan(raw_clim).any())

# wrap-around 31-day centred moving mean over 366 elements
def smooth366(a):
    a2 = np.concatenate([a, a, a])            # 3 periods
    c = np.cumsum(np.insert(a2, 0, 0.0))
    # window of 31 ending at position d (1-based) in the middle copy
    out = (c[31+366:] - c[366-15:])  # placeholder, fix below
    return None
# do it carefully: for d in 1..366 (1-based), average raw[(d-15)..(d+15)] mod 366 (366 indices, 0-based: (d-15-1)..(d+15-1))
def smooth366(a):
    N = len(a)
    ext = np.concatenate([a[-15:], a, a[:15]])
    c = np.cumsum(ext)
    # sum of ext[j-15 .. j+15] for j in 0..N-1  -> window [j-15, j+15] in ext coords, length 31
    lo = np.arange(N)          # j-15
    hi = lo + 31               # j+15+1
    s = c[hi] - c[lo]
    return s / 31.0

sm_thresh = smooth366(raw_thresh)
sm_clim   = smooth366(raw_clim)
# sanity: check manual for a couple of days
for d in [1, 60, 366, 152]:
    idx = [(d-1-15 + 16*i) % 366 for i in range(31)]
    manual = raw_thresh[idx].mean()
    print(d, sm_thresh[d-1], manual, abs(sm_thresh[d-1]-manual) < 1e-9)
print("elapsed:", round(time.time()-t0,1), "s")
np.savez_compressed('/work/doy_stats.npz', raw_thresh=raw_thresh, raw_clim=raw_clim,
                    sm_thresh=sm_thresh, sm_clim=sm_clim)
print("thr range:", np.nanmin(sm_thresh), np.nanmax(sm_thresh))
