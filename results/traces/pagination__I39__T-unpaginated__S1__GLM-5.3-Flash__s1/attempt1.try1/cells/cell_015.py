import numpy as np, datetime as dt, calendar, warnings, time

S64 = np.load('/tmp/mhw/S32.npy').astype(np.float64)
dates = [dt.date.fromisoformat(str(s)) for s in np.load('/tmp/mhw/dates.npy')]
n_base_ext = 4028
first = dates[0]
def didx(d): return (d-first).days

def mapped_doy(d):
    if d.month==2 and d.day==29: return 60
    yday = d.timetuple().tm_yday
    if calendar.isleap(d.year): return yday
    return yday if yday<=59 else yday+1

doy2dates = {}
for y in range(1992,2003):
    cur = dt.date(y,1,1)
    while cur.year==y:
        doy2dates.setdefault(mapped_doy(cur), []).append(cur)
        cur += dt.timedelta(days=1)
assert all(len(doy2dates[d])==11 for d in doy2dates if d!=60)
assert len(doy2dates[60])==3
assert sum(len(v) for v in doy2dates.values())==11*365+3

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
        X = S64[idx].reshape(len(idx), ncell)
        thr[d-1] = np.nanquantile(X, 0.9, axis=0, method='hazen')
        clim[d-1] = np.nanmean(X, axis=0)
print('pools done in %.1fs'%(time.time()-t0))

thr[59] = (thr[58]+thr[60])/2.0
clim[59] = (clim[58]+clim[60])/2.0

def smooth31(raw):
    acc = np.zeros_like(raw)
    for o in range(-15,16):
        acc += np.roll(raw, -o, axis=0)
    return acc/31.0
thr_sm = smooth31(thr)
clim_sm = smooth31(clim)

# SAVE FIRST
np.save('/tmp/mhw/thr_sm.npy', thr_sm)
np.save('/tmp/mhw/clim_sm.npy', clim_sm)
print('saved thr_sm, clim_sm')

# spot-check with a central cell (30,30)
ci=cj=30
c=ci*60+cj
d=153
wset=set()
for b in doy2dates[d]:
    for k in range(-5,6): wset.add(b+dt.timedelta(days=k))
pool = np.array([S64[didx(x),ci,cj] for x in sorted(wset)])
print('pool d=153 cell(30,30): n=%d finite=%s mean=%.6f q90=%.6f'%(pool.size, bool(np.isfinite(pool).all()), pool.mean(), np.quantile(pool,0.9,method='hazen')))
print('stored raw (day 153):    mean=%.6f q90=%.6f'%(clim[152,c], thr[152,c]))
print('stored smoothed day 153: mean=%.6f thr=%.6f'%(clim_sm[152,c], thr_sm[152,c]))

# sanity: smoothed series over June-Aug should vary smoothly; compare day-to-day changes
print('max |diff| between adjacent smoothed thr days (153..243):', float(np.abs(np.diff(thr_sm[152:243], axis=0)).max()))
print('thr_sm at (30,30) for 2010-06-01..05:', np.round(thr_sm[152:157,c],4))
print('thr_sm day60 patch check (day59 vs neighbours smooth):', round(float(thr_sm[58,c]),4), round(float(thr_sm[59,c]),4), round(float(thr_sm[60,c]),4))
