import numpy as np, xarray as xr, os, json, datetime as dt, warnings, time
t0 = time.time()
os.makedirs('/work/output', exist_ok=True)

# ---------- data ----------
base = np.load('/tmp/base.npy')   # (4028,60,60) float32, 1991-12-27..2003-01-05
tgt  = np.load('/tmp/tgt.npy')    # (92,60,60)  float32, 2019-06-01..2019-08-31
p = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(p, engine='h5netcdf')
tt = ds['time'].values.astype('datetime64[D]')
tgt_dates = tt[13665:13757]; base_dates = tt[3647:7675]
assert str(tgt_dates[0])=='2019-06-01' and str(tgt_dates[-1])=='2019-08-31'
assert str(base_dates[0])=='1991-12-27' and str(base_dates[-1])=='2003-01-05'
lat = ds['latitude'].values[551:611]; lon = ds['longitude'].values[649:709]

# sanity: NaN only at static land cells
land = ~np.isfinite(tgt).all(axis=0)
assert np.array_equal(land, ~np.isfinite(base).all(axis=0))
assert (np.isfinite(base) == np.isfinite(base[0:1])).all()
sea = ~land
print('sea cells', int(sea.sum()), 'land', int(land.sum()))

# ---------- day-of-year mapping (month/day, 1..366, Feb29=60) ----------
CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy366(d):  # d: datetime.date
    return int(CUM[d.month-1] + d.day)
def md_of_doy(d):  # -> (month, day)
    m = int(np.searchsorted(CUM, d, side='left'))
    return m, d - CUM[m-1]
for d,mday in [(1,(1,1)),(59,(2,28)),(60,(2,29)),(61,(3,1)),(152,(6,1)),(243,(8,31)),(366,(12,31))]:
    assert md_of_doy(d)==mday, (d, md_of_doy(d))
# cross-check against python calendar for every day of 1992(leap),1993,2019
import calendar
for y in (1992,1993,2019):
    days = [dt.date(y,m,dd) for m in range(1,13) for dd in range(1,calendar.monthrange(y,m)[1]+1)]
    exp  = [ (dt.date(y,3,1)-dt.date(y,1,1)).days + 1 + (0 if dd < dt.date(y,3,1) else 0) for dd in days ]
    # expected via definition: cal_doy + 1 if on/after Mar 1 in leap... build directly:
    exp = []
    for dd in days:
        if dd < dt.date(y,3,1): exp.append(dd.timetuple().tm_yday)
        elif dd == dt.date(y,3,1): exp.append(61)
        else: exp.append(61 + (dd - dt.date(y,3,1)).days)
    assert [doy366(x) for x in days] == exp, y
print('doy mapping verified')

# ---------- extension dates & pools ----------
d0 = dt.date(1991,12,27); d1 = dt.date(2003,1,5)
ext = [d0 + dt.timedelta(days=k) for k in range((d1-d0).days+1)]
assert len(ext)==4028 and ext[0]==dt.date(1991,12,27) and ext[-1]==dt.date(2003,1,5)
assert [str(x) for x in base_dates] == [x.isoformat() for x in ext]
date2idx = {d:i for i,d in enumerate(ext)}
ext_doy = np.array([doy366(d) for d in ext])
print('ext doy range', ext_doy.min(), ext_doy.max(), 'doy60 count', int((ext_doy==60).sum()))

pools = {}
for d in range(1, 367):
    if d == 60: continue
    m, day = md_of_doy(d)
    idxs = []
    for y in range(1992, 2003):
        anchor = dt.date(y, m, day)
        for k in range(-5, 6):
            idxs.append(date2idx[anchor + dt.timedelta(days=k)])
    idxs = np.asarray(idxs)
    assert idxs.size == 121 and np.unique(idxs).size == 121, d
    pools[d] = np.sort(idxs)
sizes = np.array([pools[d].size for d in pools]); print('pool sizes', sizes.min(), sizes.max())
# per-date usage check (deficit analysis)
use = np.zeros(4028, int)
for d,idxs in pools.items(): use[idxs] += 1
print('usage min/max', use.min(), use.max(), 'total', use.sum(), '= 365*121 =', 365*121)
print('least-used dates:', [(ext[i].isoformat(), int(use[i])) for i in np.argsort(use)[:12]])

# ---------- thresholds & climatology ----------
B = base.astype(np.float64).reshape(4028, -1)
thr = np.full((366, B.shape[1]), np.nan)
clm = np.full((366, B.shape[1]), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for d in range(1, 367):
        if d == 60: continue
        pool = B[pools[d]]
        thr[d-1] = np.nanpercentile(pool, 90, axis=0, method='hazen')
        clm[d-1] = np.nanmean(pool, axis=0)
# day 60 = mean of days 59 and 61
thr[59] = 0.5*(thr[58] + thr[60]); clm[59] = 0.5*(clm[58] + clm[60])
# circular 31-day centred moving mean
off = np.arange(-15,16)
w = (np.arange(366)[:,None] + off[None,:]) % 366
thr_s = thr[w].mean(axis=1); clm_s = clm[w].mean(axis=1)
np.save('/tmp/thr_s.npy', thr_s.reshape(366,60,60)); np.save('/tmp/clm_s.npy', clm_s.reshape(366,60,60))
# diagnostics at a sample sea cell
cc = np.flatnonzero(sea.ravel())[0]
print('sample cell %d:' % cc, 'clim Jun1=%.3f Aug31=%.3f' % (clm_s[152,cc], clm_s[242,cc]),
      'thr Jun1=%.3f Aug31=%.3f' % (thr_s[152,cc], thr_s[242,cc]))
print('raw (unsmoothed) thr/clim doy59,60,61 at sample:', thr[58,cc], thr[59,cc], thr[60,cc], clm[58,cc], clm[59,cc], clm[60,cc])
print('computed thresholds/climatology OK, t=%.1fs' % (time.time()-t0))
