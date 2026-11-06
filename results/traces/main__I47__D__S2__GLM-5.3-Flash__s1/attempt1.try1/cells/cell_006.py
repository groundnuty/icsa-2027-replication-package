import numpy as np, warnings, time as _t
t0 = _t.time()
sst_b = np.load('/work/sst_b.npy')
NT, NY, NX = sst_b.shape
sst_f = sst_b.reshape(NT, -1)

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

# sanity: manual Hazen == np.quantile(method='hazen'); nanquantile ignores NaN per column
chk = np.quantile(np.arange(1,11.0), 0.9, method='hazen')
assert abs(chk - 9.5) < 1e-12
nn = np.array([1.,2.,np.nan,4.])
assert abs(np.nanquantile(nn, 0.9, method='hazen') - 3.6) < 1e-12
print('hazen checks pass')

thr = np.full((366, NY*NX), np.nan, dtype=np.float64)
clm = np.full((366, NY*NX), np.nan, dtype=np.float64)
with warnings.catch_warnings():
    warnings.simplefilter('ignore')  # all-NaN slices (land) expected
    for tgt in range(1, 367):
        if tgt == 60: continue
        pool = sst_f[per_target[tgt]]                      # (P, 3600) float64, NaN kept
        thr[tgt-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
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

# diagnostics: spatial variation now present?
for cell in [(0,0),(30,30),(59,59)]:
    print('day180 cell%s: thr %.4f clm %.4f' % (cell, thr_s[179,cell[0],cell[1]], clm_s[179,cell[0],cell[1]]))
print('day165 thr spread over cells: %.4f .. %.4f' % (np.nanmin(thr_s[164]), np.nanmax(thr_s[164])))
