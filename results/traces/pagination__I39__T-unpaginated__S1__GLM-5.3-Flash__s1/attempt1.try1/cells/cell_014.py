import numpy as np, datetime as dt, calendar, warnings, time
from collections import Counter

S64 = np.load('/tmp/mhw/S32.npy').astype(np.float64)
dates = [dt.date.fromisoformat(str(s)) for s in np.load('/tmp/mhw/dates.npy')]
n_base_ext = 4028
first = dates[0]
assert str(first)=='1991-12-27' and str(dates[n_base_ext-1])=='2003-01-05'
assert str(dates[n_base_ext])=='2010-06-01' and str(dates[-1])=='2010-08-31'
def didx(d): return (d-first).days

def mapped_doy(d):
    if d.month==2 and d.day==29: return 60
    yday = d.timetuple().tm_yday
    if calendar.isleap(d.year): return yday
    return yday if yday<=59 else yday+1

# spec examples
assert mapped_doy(dt.date(2010,6,1))==153
assert mapped_doy(dt.date(2010,8,31))==244
assert mapped_doy(dt.date(2000,2,29))==60
assert mapped_doy(dt.date(1999,3,1))==61 and mapped_doy(dt.date(2000,3,1))==61
assert mapped_doy(dt.date(1999,12,31))==366 and mapped_doy(dt.date(2000,12,31))==366
assert mapped_doy(dt.date(1999,2,28))==59

doy2dates = {}
for y in range(1992,2003):
    cur = dt.date(y,1,1)
    while cur.year==y:
        doy2dates.setdefault(mapped_doy(cur), []).append(cur)
        cur += dt.timedelta(days=1)
cnt = Counter({d:len(v) for d,v in doy2dates.items()})
print('baseline dates per doy (should be 11 for d!=60, 3 for d=60):', dict(cnt))
print('doy 60 baseline dates:', [str(x) for x in doy2dates[60]])

ncell = 60*60
thr = np.full((366,ncell), np.nan)
clim = np.full((366,ncell), np.nan)

t0=time.time()
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for d in range(1,367):
        if d==60: continue
        wset = set()
        for b in doy2dates[d]:
            for k in range(-5,6):
                wset.add(b+dt.timedelta(days=k))
        idx = np.array(sorted(didx(x) for x in wset))
        assert idx.min()>=0 and idx.max()<=n_base_ext-1
        X = S64[idx].reshape(len(idx), ncell)
        thr[d-1] = np.nanquantile(X, 0.9, axis=0, method='hazen')
        clim[d-1] = np.nanmean(X, axis=0)
print('pools done in %.1fs'%(time.time()-t0))

# patch day 60 (index 59)
thr[59] = (thr[58]+thr[60])/2.0
clim[59] = (clim[58]+clim[60])/2.0

def smooth31(raw):
    acc = np.zeros_like(raw)
    for o in range(-15,16):
        acc += np.roll(raw, -o, axis=0)
    return acc/31.0
thr_sm = smooth31(thr)
clim_sm = smooth31(clim)

# --- validations ---
rng = np.random.default_rng(0)
xs = np.sort(rng.normal(size=50))
def hazen_manual(x,p):
    n=len(x); h=p*n+0.5; j=int(np.floor(h)); g=h-j
    if j<=0: return x[0]
    if j>=n: return x[-1]
    return x[j-1]+g*(x[j]-x[j-1])
assert abs(np.quantile(xs,0.9,method='hazen')-hazen_manual(xs,0.9))<1e-12
print('hazen check OK')

r = rng.normal(size=(366,3))
sm = smooth31(r)
for d0 in [0,1,100,184,365]:
    vals = np.array([r[(d0+o)%366,:] for o in range(-15,16)])
    assert np.allclose(sm[d0], vals.mean(axis=0)), d0
print('smoothing wrap check OK')

# spot-check one pool by brute force recomputation (cell 0, doy 153)
c=0; d=153
wset=set()
for b in doy2dates[153]:
    for k in range(-5,6): wset.add(b+dt.timedelta(days=k))
pool = np.array([S64[didx(x),0,0] for x in sorted(wset)])
assert pool.size==121 and np.isfinite(pool).all()
print('pool d=153 cell0: n=%d mean=%.6f q90=%.6f'%(pool.size, pool.mean(), np.quantile(pool,0.9,method='hazen')))
print('stored:            mean=%.6f q90=%.6f'%(clim[152,0], thr[152,0]))

np.save('/tmp/mhw/thr_sm.npy', thr_sm)
np.save('/tmp/mhw/clim_sm.npy', clim_sm)
print('saved. thr_sm shape', thr_sm.shape)
