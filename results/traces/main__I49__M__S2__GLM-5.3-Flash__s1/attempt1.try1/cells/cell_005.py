import numpy as np, xarray as xr, os, json, datetime as dt, warnings, time
t0 = time.time()
os.makedirs('/work/output', exist_ok=True)

base = np.load('/tmp/base.npy'); tgt = np.load('/tmp/tgt.npy')
p = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(p, engine='h5netcdf')
tt = ds['time'].values.astype('datetime64[D]')
tgt_dates = tt[13665:13757]; base_dates = tt[3647:7675]
land = ~np.isfinite(tgt).all(axis=0); sea = ~land

CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy366(d): return int(CUM[d.month-1] + d.day)
def md_of_doy(d):
    m = int(np.searchsorted(CUM, d, side='left')); return m, d - CUM[m-1]
for d,mday in [(1,(1,1)),(59,(2,28)),(60,(2,29)),(61,(3,1)),(153,(6,1)),(182,(6,30)),(244,(8,31)),(366,(12,31))]:
    assert md_of_doy(d)==mday, (d, md_of_doy(d))
import calendar
for y in (1992,1993,2019):
    days = [dt.date(y,m,dd) for m in range(1,13) for dd in range(1,calendar.monthrange(y,m)[1]+1)]
    exp = []
    for dd in days:
        if dd < dt.date(y,3,1): exp.append(dd.timetuple().tm_yday)
        else: exp.append(61 + (dd - dt.date(y,3,1)).days)
    assert [doy366(x) for x in days] == exp, y
print('doy mapping verified (Jun1=153, Aug31=244)')

d0 = dt.date(1991,12,27); d1 = dt.date(2003,1,5)
ext = [d0 + dt.timedelta(days=k) for k in range((d1-d0).days+1)]
assert len(ext)==4028 and [str(x) for x in base_dates] == [x.isoformat() for x in ext]
date2idx = {d:i for i,d in enumerate(ext)}
pools = {}
for d in range(1, 367):
    if d == 60: continue
    m, day = md_of_doy(d)
    idxs = []
    for y in range(1992, 2003):
        anchor = dt.date(y, m, day)
        for k in range(-5, 6): idxs.append(date2idx[anchor + dt.timedelta(days=k)])
    idxs = np.asarray(idxs); assert idxs.size==121 and np.unique(idxs).size==121, d
    pools[d] = idxs
use = np.zeros(4028, int)
for d,idxs in pools.items(): use[idxs] += 1
assert use.sum() == 365*121
print('pools built; usage min/max', use.min(), use.max())
print('least-used dates:', [(ext[i].isoformat(), int(use[i])) for i in np.argsort(use)[:8]])

B = base.astype(np.float64).reshape(4028, -1)
thr = np.full((366, B.shape[1]), np.nan); clm = np.full((366, B.shape[1]), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for d in range(1, 367):
        if d == 60: continue
        pool = B[pools[d]]
        thr[d-1] = np.nanpercentile(pool, 90, axis=0, method='hazen')
        clm[d-1] = np.nanmean(pool, axis=0)
thr[59] = 0.5*(thr[58] + thr[60]); clm[59] = 0.5*(clm[58] + clm[60])
off = np.arange(-15,16); w = (np.arange(366)[:,None] + off[None,:]) % 366
thr_s = thr[w].mean(axis=1); clm_s = clm[w].mean(axis=1)
np.save('/tmp/thr_s.npy', thr_s.reshape(366,60,60)); np.save('/tmp/clm_s.npy', clm_s.reshape(366,60,60))
cc = int(np.flatnonzero(sea.ravel())[0])
print('sample sea cell[%d]: clim Jun1=%.3f Aug31=%.3f; thr Jun1=%.3f Aug31=%.3f' %
      (cc, clm_s[152,cc], clm_s[243,cc], thr_s[152,cc], thr_s[243,cc]))
print('raw thr/clim doy59,60,61 at sample:', np.round(thr[58:61,cc],3), np.round(clm[58:61,cc],3))
print('done thresholds/clim, t=%.1fs' % (time.time()-t0))
