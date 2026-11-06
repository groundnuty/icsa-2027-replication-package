import numpy as np, json, datetime as dt, os, time, warnings

t0 = time.time()
ext_dates = [d for d in json.load(open('cache/manifest.json')) if d < '2007']
tgt_dates = sorted(d for d in json.load(open('cache/manifest.json')) if d >= '2007')
ext_dates.sort(); 
# robust: define explicitly
def build_dates(y0,m0,d0,y1,m1,d1):
    a = dt.date(y0,m0,d0); b = dt.date(y1,m1,d1)
    return [(a+dt.timedelta(days=i)).strftime('%Y%m%d') for i in range((b-a).days+1)]
ext_dates = build_dates(1991,12,27, 2003,1,5)
tgt_dates = build_dates(2007,6,1, 2007,8,31)
assert len(ext_dates)==4028 and len(tgt_dates)==92

def load_stack(dates):
    out = np.empty((len(dates), 60, 60), dtype='float64')
    for i,d in enumerate(dates):
        out[i] = np.load(f'cache/arr/{d}.npy')
    return out

SST = load_stack(ext_dates)      # (4028,60,60) float64
SST_t = load_stack(tgt_dates)    # (92,60,60) float64
print('loaded', SST.shape, SST_t.shape, f'{time.time()-t0:.1f}s', flush=True)

doy_ext = np.array([dt.date(int(d[:4]),int(d[4:6]),int(d[6:8])).timetuple().tm_yday for d in ext_dates])
doy_tgt = np.array([dt.date(int(d[:4]),int(d[4:6]),int(d[6:8])).timetuple().tm_yday for d in tgt_dates])
print('target doys', doy_tgt[0], '..', doy_tgt[-1])
print('ext leap years contain doy60:', [y for y in range(1992,2003) if (dt.date(y,3,1)-dt.date(y,1,1)).days==60])

# Sea cells: finite on every target day
sea = np.isfinite(SST_t).all(axis=0)
print('sea cells:', int(sea.sum()), 'of', sea.size)

# Pools -> raw climatology & threshold
clim_raw = np.full((366,60,60), np.nan)  # will fill 1..365 except 60, then 60
thr_raw  = np.full((366,60,60), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter('ignore', RuntimeWarning)
    for d in range(1, 367):
        if d == 60: continue
        sel = np.where(np.abs(doy_ext.astype('int64') - d) <= 5)[0]
        pool = SST[sel]
        clim_raw[d-1] = np.nanmean(pool, axis=0)
        thr_raw[d-1]  = np.nanquantile(pool, 0.9, axis=0, method='hazen')
print('pools done', f'{time.time()-t0:.1f}s', flush=True)

clim = clim_raw.copy(); thr = thr_raw.copy()
clim[59] = 0.5*(clim_raw[58] + clim_raw[60])   # day 60 = mean of days 59,61
thr[59]  = 0.5*(thr_raw[58]  + thr_raw[60])

# circular (wrap-around) centred 31-day moving mean
ar = np.arange(366)
def circ31(V):
    out = np.zeros_like(V)
    for off in range(-15, 16):
        out += V[(ar + off) % 366]
    return out / 31.0
clim_s = circ31(clim)
thr_s  = circ31(thr)
print('smoothing done', f'{time.time()-t0:.1f}s', flush=True)
print('clim_s finite over sea:', bool(np.isfinite(clim_s[:, sea]).all()),
      'thr_s finite over sea:', bool(np.isfinite(thr_s[:, sea]).all()))

np.save('cache/clim_s.npy', clim_s); np.save('cache/thr_s.npy', thr_s)
np.save('cache/sea.npy', sea); np.save('cache/SST_t.npy', SST_t)
np.save('cache/doy_tgt.npy', doy_tgt)
json.dump({'ext_dates': ext_dates, 'tgt_dates': tgt_dates}, open('cache/dates.json','w'))
print('saved. total', f'{time.time()-t0:.1f}s')
