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
        for idx in cand: offs.append(idx + o)
    per_target[tgt] = np.asarray(sorted(set(offs)), dtype=np.int64)

thr = np.full((366, NY*NX), np.nan, dtype=np.float64)
clm = np.full((366, NY*NX), np.nan, dtype=np.float64)
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for tgt in range(1, 367):
        if tgt == 60: continue
        pool = sst_f[per_target[tgt]]
        thr[tgt-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        clm[tgt-1] = np.nanmean(pool, axis=0)
thr = thr.reshape(366, NY, NX); clm = clm.reshape(366, NY, NX)
thr[59] = 0.5*(thr[58] + thr[60]); clm[59] = 0.5*(clm[58] + clm[60])
print('raw stats recomputed (per-cell) t=%.1fs' % (_t.time()-t0))
print('raw clm day178 cell(30,30): %.4f K (direct pool mean was 284.40)' % clm[177,30,30])

def smooth_circ(x):  # x (366,...) -> centred 31-day mean, wrap mod 366
    pc2 = np.concatenate([x[351:], x, x[:15]], axis=0)          # 396 = 15+366+15
    c = np.concatenate([np.zeros((1,)+x.shape[1:], np.float64), np.cumsum(pc2, axis=0)], axis=0)
    return (c[31:397] - c[:366]) / 31.0

thr_s = smooth_circ(thr); clm_s = smooth_circ(clm)
print('fixed smoothing done t=%.1fs' % (_t.time()-t0))

# explicit verification of the smoothing on several days/cells
idx = np.arange(366)
def explicit(x, d0):  # d0 1-based
    days = [((d0-1+k) % 366) for k in range(-15, 16)]
    return np.mean([x[j] for j in days], axis=0)
for d0 in [1, 2, 60, 180, 240, 365, 366]:
    for cell in [(0,0), (30,30), (59,59)]:
        a = thr_s[d0-1, cell[0], cell[1]]; b = explicit(thr, d0)[cell[0], cell[1]]
        assert abs(a-b) < 1e-9, (d0, cell, a, b)
print('smoothing verified explicitly for days 1,2,60,180,240,365,366 x 3 cells')
print('day180 cell(30,30): thr %.4f clm %.4f  (degC %.2f/%.2f)' %
      (thr_s[179,30,30], clm_s[179,30,30], thr_s[179,30,30]-273.15, clm_s[179,30,30]-273.15))
print('day152 cell(30,30): thr %.4f clm %.4f  (degC %.2f/%.2f)' %
      (thr_s[151,30,30], clm_s[151,30,30], thr_s[151,30,30]-273.15, clm_s[151,30,30]-273.15))
print('day243 cell(30,30): thr %.4f clm %.4f  (degC %.2f/%.2f)' %
      (thr_s[242,30,30], clm_s[242,30,30], thr_s[242,30,30]-273.15, clm_s[242,30,30]-273.15))

# end-to-end: rebuild pool for doy 180 & threshold via dates for cell (30,30), then smoothed day 180
import datetime as dtt
def doy_of(y, m, d):
    return dtt.date(y, m, d).timetuple().tm_yday
offs2 = set()
for o in range(-5, 6):
    for y in range(1992, 2003):
        ld = 29 if (y%4==0 and (y%100!=0 or y%400==0)) else 28
        for (mm, dd) in [(2,29)] if False else []:
            pass
        # candidate baseline dates with doy 180 shifted by o
for y in range(1992, 2003):
    leapY = (y%4==0 and (y%100!=0 or y%400==0))
    # find month/day with tm_yday == 180
    for mm in range(1, 13):
        ld = [31,29 if leapY else 28,31,30,31,30,31,31,30,31,30,31][mm-1]
        for dd in range(1, ld+1):
            if doy_of(y, mm, dd) == 180:
                base = dtt.date(y, mm, dd)
                for k in range(-5, 6):
                    q = base + dtt.timedelta(days=k)
                    if dtt.date(1991,12,27) <= q <= dtt.date(2003,1,5):
                        i = (q - dtt.date(1991,12,27)).days
                        offs2.add(i)
vals = sst_b[sorted(offs2), 30, 30]
v = np.sort(vals[np.isfinite(vals)]); n = len(v)
h = n*0.9 - 0.5; lo = int(np.floor(h)); hi = int(np.ceil(h))
q180 = v[lo] + (h-lo)*(v[hi]-v[lo])
man180 = np.mean([thr[j,30,30] for j in [((179+k)%366) for k in range(-15,16)]])
print('end-to-end doy180 cell(30,30): pool n=%d q90=%.4f | smoothed thr_s=%.4f | explicit=%.4f | match=%s' %
      (n, q180, thr_s[179,30,30], man180, abs(q180-thr[179,30,30])<1e-9 and abs(man180-thr_s[179,30,30])<1e-9))

np.save('/work/thr_s.npy', thr_s); np.save('/work/clm_s.npy', clm_s)
np.save('/work/thr_raw.npy', thr); np.save('/work/clm_raw.npy', clm)
print('saved (overwritten) thr_s/clm_s + raw arrays')
