import numpy as np, warnings, time as _t
t0 = _t.time()
sst_b = np.load('/work/sst_b.npy')
NT, NY, NX = sst_b.shape
sst_f = sst_b.reshape(NT, -1)

def hazen_col(pool):
    P, C = pool.shape
    part = np.sort(pool, axis=0)
    n = np.isfinite(part).sum(axis=0)
    h = n*0.9 - 0.5
    ilo = np.clip(np.floor(h).astype(int), 0, P-1)
    ihi = np.clip(np.ceil(h).astype(int), 0, P-1)
    nn1 = np.maximum(n-1, 0)
    ilo = np.minimum(ilo, nn1); ihi = np.minimum(ihi, nn1)
    cols = np.arange(C)
    vlo = part[ilo, cols]; vhi = part[ihi, cols]
    g = h - np.floor(h)
    with np.errstate(invalid='ignore'):
        q = vlo + g*(vhi - vlo)
    return np.where(n > 0, q, np.nan)

rng = np.random.default_rng(42)
ok = True
for trial in range(300):
    P = int(rng.integers(2, 40)); C = 12
    A = rng.normal(size=(P, C)); A[rng.random((P, C)) < 0.25] = np.nan
    if rng.random() < 0.2: A[:, 3] = np.nan
    q_np = np.nanquantile(A, 0.9, axis=0, method='hazen')
    q_m = hazen_col(A)
    if not np.isclose(q_np, q_m, equal_nan=True, atol=1e-12).all():
        ok = False; break
print('fixed hazen_col vs nanquantile (300 trials):', 'ALL MATCH' if ok else 'MISMATCH')

bd = np.arange('1991-12-27', '2003-01-06', dtype='datetime64[D]')
bmonths = bd.astype('datetime64[M]').astype(int) % 12 + 1
bdays = (bd - bd.astype('datetime64[M]')).astype(int) + 1
yrs = bd.astype('datetime64[Y]').astype(int) + 1970
leap = ((yrs % 4 == 0) & ((yrs % 100 != 0) | (yrs % 400 == 0)))
cump = np.array([0,31,59,90,120,151,181,212,243,273,304,334])
bdoy = cump[bmonths-1] + bdays + (leap & (bmonths > 2)).astype(int)

per_target = {}
for tgt in range(1, 367):
    if tgt == 60: continue
    offs = []
    for o in range(-5, 6):
        nd = bd + np.timedelta64(o, 'D')
        cand = np.flatnonzero((bdoy == tgt) & (nd >= bd[0]) & (nd <= bd[-1]))
        for idx in cand:
            offs.append(idx + o)
    per_target[tgt] = np.asarray(sorted(offs), dtype=np.int64)

# brute-force independent check of pools for a few doys
import datetime as dt
base0 = dt.date(1991,12,27)
for tgt in [1, 59, 180, 365, 366]:
    good = []
    for o in range(-5, 6):
        nd = bd + np.timedelta64(o, 'D')
        for idx in np.flatnonzero(bdoy == tgt):
            if bd[0] <= nd[idx] <= bd[-1]: good.append(idx + o)
    good = sorted(set(good))
    assert good == list(per_target[tgt]), tgt
    # also: brute force by real dates
    bf = set()
    for d in bd:
        dd = d.astype(dt.date) if hasattr(d.astype(dt.date),'timetuple') else None
    print('doy %3d pool size %3d (offsets %d..%d) OK' % (tgt, len(good), good[0], good[-1]))

thr = np.full((366, NY*NX), np.nan, dtype=np.float64)
clm = np.full((366, NY*NX), np.nan, dtype=np.float64)
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for tgt in range(1, 367):
        if tgt == 60: continue
        pool = sst_f[per_target[tgt]]
        thr[tgt-1] = hazen_col(pool)
        clm[tgt-1] = np.nanmean(pool, axis=0)
thr = thr.reshape(366, NY, NX); clm = clm.reshape(366, NY, NX)
print('per-cell quantiles & means done t=%.1fs' % (_t.time()-t0))

thr[59] = 0.5*(thr[58] + thr[60]); clm[59] = 0.5*(clm[58] + clm[60])
pt = np.concatenate([thr[335:], thr, thr[:15]], axis=0)
pc = np.concatenate([clm[335:], clm, clm[:15]], axis=0)
s = pt.cumsum(axis=0); s[31:] -= s[:-31]; thr_s = s/31.0
s = pc.cumsum(axis=0); s[31:] -= s[:-31]; clm_s = s/31.0
np.save('/work/thr_s.npy', thr_s); np.save('/work/clm_s.npy', clm_s)
print('smoothing done t=%.1fs' % (_t.time()-t0))
for cell in [(0,0),(30,30),(59,59)]:
    print('day180 cell%s: thr %.4f clm %.4f' % (cell, thr_s[179,cell[0],cell[1]], clm_s[179,cell[0],cell[1]]))
print('day165 thr over cells: %.4f .. %.4f | non-finite cells: %d' %
      (np.nanmin(thr_s[164]), np.nanmax(thr_s[164]), np.sum(~np.isfinite(thr_s[164]))))
