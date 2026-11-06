import numpy as np, time as _t

z = np.load('/work/interim.npz')
sst_t, sst_b, sea = z['sst_t'], z['sst_b'], z['sea']
nlat, nlon = 60, 60
NC = nlat*nlon
origin = np.datetime64('1991-12-27','D')
def d2i(d64): return int((d64 - origin)//np.datetime64(1,'D'))

def doy_to_md(d):
    leap = d >= 61
    days = [31,29,31,30,31,30,31,31,30,31,30,31] if leap else [31,28,31,30,31,30,31,31,30,31,30,31]
    for m, nd in enumerate(days):
        if d <= nd: return m+1, d
        d -= nd
    raise ValueError(d)

def md_to_doy(m, dd):
    if (m,dd) == (2,29): return 60
    days = [31,28,31,30,31,30,31,31,30,31,30,31]
    cum = 0
    for mm in range(1, m):
        cum += days[mm-1]
    doy = cum + dd
    if m > 2: doy += 1   # leap-year offset (Feb 29 owns number 60)
    return doy

# sanity checks under the task's numbering
assert md_to_doy(1,1)==1 and md_to_doy(2,28)==59 and md_to_doy(2,29)==60 and md_to_doy(3,1)==61
assert md_to_doy(6,1)==153 and md_to_doy(8,31)==244 and md_to_doy(12,31)==366 and md_to_doy(5,31)==152
assert doy_to_md(61)==(3,1) and doy_to_md(59)==(2,28) and doy_to_md(1)==(1,1) and doy_to_md(366)==(12,31)
assert doy_to_md(153)==(6,1) and doy_to_md(244)==(8,31) and doy_to_md(183)==(7,1) and doy_to_md(214)==(8,1)
print("mapping OK; target doys: 153..244")

def hazen90_cols(A):
    n = np.isfinite(A).sum(axis=0)
    S = np.sort(A, axis=0)
    out = np.full(A.shape[1], np.nan)
    ok = n > 0
    v = 0.9*n[ok] - 0.5
    vm = np.clip(v, 0.0, n[ok]-1)
    j = np.floor(vm).astype(np.int64)
    jj = np.clip(j+1, 0, n[ok]-1)
    g = vm - j
    cols = np.arange(n[ok].size)
    out[ok] = S[j, cols] + g*(S[jj, cols] - S[j, cols])
    return out, n

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
    climd = np.full(NC, np.nan)
    ok = n>0
    climd[ok] = np.nanmean(A[:, ok], axis=0)
    thr[d]  = q.reshape(nlat, nlon)
    clim[d] = climd.reshape(nlat, nlon)
    min_pool = np.minimum(min_pool, n)
print("pool loop done in %.1f s" % (_t.time()-t0))
print("min pool size overall:", min_pool.min(), " cells with pool<100:", int((min_pool<100).sum()), " empty:", int((min_pool==0).sum()))

thr[60]  = 0.5*(thr[59] + thr[61])
clim[60] = 0.5*(clim[59] + clim[61])

def smooth31(a):
    idxs = (np.arange(366)[:,None] + np.arange(-15,16)[None,:]) % 366
    return a[idxs].mean(axis=1)

thr_s  = smooth31(thr)
clim_s = smooth31(clim)
td = slice(152, 245)  # doys 153..244
print("NaNs in smoothed thr over target doys:", int(np.isnan(thr_s[td]).sum()))
print("NaNs in smoothed clim over target doys:", int(np.isnan(clim_s[td]).sum()))
print("target thr range: %.3f .. %.3f K" % (np.nanmin(thr_s[td]), np.nanmax(thr_s[td])))

np.savez_compressed('/work/thr_clim.npz', thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s)
print("saved thr_clim")
