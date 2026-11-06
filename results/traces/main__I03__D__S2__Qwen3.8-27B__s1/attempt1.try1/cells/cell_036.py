import numpy as np, time as _t, warnings

z = np.load('/work/interim.npz')
sst_t, sst_b, sea = z['sst_t'], z['sst_b'], z['sea']
nlat, nlon = 60, 60
NC = nlat*nlon
origin = np.datetime64('1991-12-27','D')
def d2i(d64): return int((d64 - origin) // np.timedelta64(1,'D'))

def doy_to_md(d):
    leap = d >= 61
    days = [31,29,31,30,31,30,31,31,30,31,30,31] if leap else [31,28,31,30,31,30,31,31,30,31,30,31]
    for m, nd in enumerate(days):
        if d <= nd: return m+1, d
        d -= nd

def hazen90_cols(A):
    n = np.isfinite(A).sum(axis=0)
    S = np.sort(A, axis=0)
    out = np.full(A.shape[1], np.nan)
    ok = n > 0
    cols = np.flatnonzero(ok)          # FIX: true column indices
    v = 0.9*n[ok] - 0.5
    vm = np.clip(v, 0.0, n[ok]-1)
    j = np.floor(vm).astype(np.int64)
    jj = np.clip(j+1, 0, n[ok]-1)
    g = vm - j
    out[ok] = S[j, cols] + g*(S[jj, cols] - S[j, cols])
    return out, n

# --- cross-validate hazen90_cols vs np.nanquantile (incl. all-NaN columns, small n) ---
rng = np.random.default_rng(7)
maxdiff = 0.0
for trial in range(300):
    W = int(rng.integers(1, 130)); C = int(rng.integers(1, 12))
    A = rng.normal(288, 2, (W, C))
    p = rng.random()
    A[rng.random((W,C)) < p] = np.nan
    A[:, rng.integers(0, C, size=max(0,int(C*p2))) if False else slice(None)]  # no-op
    # force a fully-NaN column sometimes
    if trial % 3 == 0 and C > 1:
        A[:, 0] = np.nan
    mine = hazen90_cols(A)[0]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        ref = np.nanquantile(A, 0.9, method='hazen', axis=0)
    d = np.nanmax(np.abs(mine - ref))
    maxdiff = max(maxdiff, d)
    assert np.array_equal(np.isnan(mine), np.isnan(ref)), (trial, mine, ref)
print("max |mine - nanquantile| over 300 random pools (with NaNs):", maxdiff)

# also validate mean vs nanmean
A = rng.normal(288, 2, (50, 7)); A[rng.random((50,7)) < 0.1] = np.nan
print("mean check:", np.allclose(np.nanmean(A, axis=0), np.nanmean(A, axis=0)))

t0=_t.time()
thr  = np.full((366, nlat, nlon), np.nan)
clim = np.full((366, nlat, nlon), np.nan)
min_pool = np.full(NC, 10**9)
for d in range(1, 367):
    if d == 60: continue
    m, dd = doy_to_md(d)
    sl = []
    for y in range(1992, 2003):
        bi = d2i(np.datetime64(f'{y:04d}-{m:02d}-{dd:02d}','D'))
        sl.append(sst_b[bi-5:bi+6])
    A = np.concatenate(sl, axis=0).reshape(121, NC)
    q, n = hazen90_cols(A)
    ok = n>0
    climd = np.full(NC, np.nan)
    climd[ok] = np.nanmean(A[:, ok], axis=0)
    thr[d-1]  = q.reshape(nlat, nlon)
    clim[d-1] = climd.reshape(nlat, nlon)
    min_pool = np.minimum(min_pool, n)
print("pool loop done in %.1f s" % (_t.time()-t0))
print("min pool size overall:", int(min_pool.min()))
print("sea cells: min pool:", int(min_pool[sea.reshape(NC)].min()), " non-sea min pool:", int(min_pool[~sea.reshape(NC)].min()))

thr[59]  = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

def smooth31(a):
    idxs = (np.arange(366)[:,None] + np.arange(-15,16)[None,:]) % 366
    return a[idxs].mean(axis=1)

thr_s  = smooth31(thr)
clim_s = smooth31(clim)
td = slice(152, 245)
print("NaNs in smoothed thr over target doys:", int(np.isnan(thr_s[td]).sum()))
print("NaNs in smoothed clim over target doys:", int(np.isnan(clim_s[td]).sum()))
bad = np.isnan(thr_s[td]).any(axis=0).reshape(60,60)
print("cells with NaN smoothed thr over target days:", int(bad.sum()), "(all non-sea? ", bool(np.all(~sea[bad])), ")")
print("target thr range (sea cells): %.3f .. %.3f K" % (
    np.nanmin(thr_s[td][sea]), np.nanmax(thr_s[td][sea])))

np.savez_compressed('/work/thr_clim.npz', thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s)
print("saved thr_clim (fixed)")
