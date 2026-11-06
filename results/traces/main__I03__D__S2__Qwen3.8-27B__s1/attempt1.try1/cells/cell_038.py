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
    cols = np.flatnonzero(ok)
    v = 0.9*n[ok] - 0.5
    vm = np.clip(v, 0.0, n[ok]-1)
    j = np.floor(vm).astype(np.int64)
    jj = np.clip(j+1, 0, n[ok]-1)
    g = vm - j
    out[ok] = S[j, cols] + g*(S[jj, cols] - S[j, cols])
    return out, n

t0=_t.time()
thr  = np.full((366, nlat, nlon), np.nan)
clim = np.full((366, nlat, nlon), np.nan)
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
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        climd[ok] = np.nanmean(A[:, ok], axis=0)
    thr[d-1]  = q.reshape(nlat, nlon)
    clim[d-1] = climd.reshape(nlat, nlon)
print("pool loop done in %.1f s" % (_t.time()-t0))

thr[59]  = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

def smooth31(a):
    idxs = (np.arange(366)[:,None] + np.arange(-15,16)[None,:]) % 366
    return a[idxs].mean(axis=1)

thr_s  = smooth31(thr)
clim_s = smooth31(clim)
td = slice(152, 245)
tts = thr_s[td]
sv = sea & np.isfinite(tts).all(axis=0)
print("cells with NaN smoothed thr over target days:", int(np.isnan(tts).any(axis=0).sum()), "| all non-sea:", bool(np.all(~sea[np.isnan(tts).any(axis=0)])))
print("sea cells with fully finite target threshold:", int(sv.sum()))
print("target thr range (sea cells): %.4f .. %.4f K" % (np.nanmin(tts[:, sv]), np.nanmax(tts[:, sv])))
print("clim range over target doys (sea): %.4f .. %.4f K" % (np.nanmin(clim_s[td][:, sv]), np.nanmax(clim_s[td][:, sv])))

np.savez_compressed('/work/thr_clim.npz', thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s)
print("saved thr_clim (fixed)")
