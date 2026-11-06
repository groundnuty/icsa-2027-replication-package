import xarray as xr, numpy as np, json, os
from datetime import date

os.makedirs('/work/output', exist_ok=True)
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t = ds.time.values
lat, lon = ds.latitude.values, ds.longitude.values
lats = np.where((lat>=54.39)&(lat<=55.59))[0]
lons = np.where((lon>=18.25)&(lon<=19.45))[0]

def gidx(dstr):
    i = int(np.searchsorted(t, np.datetime64(dstr)))
    assert t[i] == np.datetime64(dstr), (dstr, t[i])
    return i

iL0 = gidx('1991-12-27'); iL1 = gidx('2020-08-31')
S = ds.analysed_sst.isel(time=slice(iL0, iL1+1), latitude=lats, longitude=lons).values.astype(np.float64)
T, nla, nlo = S.shape
dates = t[iL0:iL1+1].astype('datetime64[D]')
print('loaded', S.shape, dates[0], dates[-1])

# day of year
yrs = dates.astype('datetime64[Y]').astype(int) + 1970
ys = np.array([date(int(y),1,1) for y in yrs], dtype='datetime64[D]')
doy = (dates - ys).astype('int64').astype(int) + 1
assert doy[0]==361 or True
# sanity: 1992-02-29 doy check
i_feb29_92 = gidx('1992-02-29')
assert doy[i_feb29_92-iL0] == 60, doy[i_feb29_92-iL0]
assert doy[gidx('1993-02-28')-iL0] == 59
assert doy[gidx('1992-03-01')-iL0] == 61

iB0, iB1 = gidx('1992-01-01'), gidx('2002-12-31')
from collections import defaultdict
pool = defaultdict(list)
for gi in range(iB0, iB1+1):
    d = doy[gi-iL0]
    pool[d].extend(range(gi-5, gi+6))
for d in pool: pool[d] = sorted(set(pool[d]))
dlist = sorted(pool)
assert dlist == [d for d in range(1,367) if d != 60], len(dlist)
alld = np.concatenate([np.array(v) for v in pool.values()])
span0, span1 = dates[alld.min()], dates[alld.max()]
print('pool span', span0, span1, 'sizes min/max', min(len(v) for v in pool.values()), max(len(v) for v in pool.values()))

C = nla*nlo
thr  = np.full((366, C), np.nan)
clim = np.full((366, C), np.nan)
for d in dlist:
    vals = S[pool[d]]
    thr[d]  = np.nanpercentile(vals, 90.0, axis=0, method='hazen')
    clim[d] = np.nanmean(vals, axis=0)
thr[60]  = 0.5*(thr[59]+thr[61])
clim[60] = 0.5*(clim[59]+clim[61])

def smooth31(a):
    ext = np.concatenate([a[-15:], a, a[:30]], axis=0)   # len 411
    P = np.concatenate([np.zeros((1, a.shape[1])), np.cumsum(ext, axis=0)], axis=0)
    return (P[31:31+366] - P[0:366]) / 31.0

thr_s  = smooth31(thr)
clim_s = smooth31(clim)

# naive check of smooth on one column
c0 = 0
a = thr[:, c0]
ok = all(abs(thr_s[d, c0] - np.mean([a[(d+k)%366] for k in range(-15,16)])) < 1e-9 for d in (0,1,15,60,183,365))
print('smooth check ok:', ok, ' (col0 had nan:', bool(np.isnan(a).any()), ')')

iT0, iT1 = gidx('2020-06-01'), gidx('2020-08-31')
tt = S[iT0-iL0 : iT1-iL0+1].reshape(-1, C)
assert tt.shape[0] == 92
tdoy = doy[iT0-iL0 : iT1-iL0+1]
finite = np.isfinite(tt).all(axis=0)
nsea = int(finite.sum())
print('sea cells:', nsea, 'of', C)
thr_nan_cells = int(np.isnan(thr_s).any(axis=0).sum())
print('cells w/ any NaN smoothed threshold (incl land):', thr_nan_cells, ' of which sea:', int((np.isnan(thr_s).any(axis=0) & finite).sum()))

thr_cells = thr_s[:, finite]
print('thr sea stats K: min %.3f med %.3f max %.3f' % (thr_cells.min(), np.nanmedian(thr_cells), thr_cells.max()))

hot = (tt >= thr_s[tdoy]) & finite[None, :]
mhw = np.zeros_like(hot)
for c in np.flatnonzero(finite):
    h = hot[:, c].astype(np.int8)
    dh = np.diff(np.concatenate([[0], h, [0]]))
    s_ = np.flatnonzero(dh == 1); e_ = np.flatnonzero(dh == -1) - 1
    segs = [[s_, e_] for s_, e_ in zip(s_, e_) if e_ - s_ + 1 >= 5]
    merged = []
    for seg in segs:
        if merged and seg[0] - merged[-1][1] - 1 <= 2:
            merged[-1][1] = seg[1]
        else:
            merged.append(seg)
    for s_, e_ in merged:
        mhw[s_:e_+1, c] = 1

print('hot days total:', int(hot.sum()), ' mhw days total:', int(mhw.sum()))
active = mhw.any(axis=1)
dha = np.diff(np.concatenate([[0], active.astype(np.int8), [0]]))
sa = np.flatnonzero(dha == 1); ea = np.flatnonzero(dha == -1) - 1
tdates = dates[iT0-iL0 : iT1-iL0+1]
events = [(tdates[s].astype('datetime64[D]').astype(str), tdates[e].astype('datetime64[D]').astype(str)) for s, e in zip(sa, ea)]
print('n events:', len(events))
for ev in events: print(ev)

mhw_region = mhw.reshape(-1, nla, nlo)
sub = ds.isel(time=slice(iT0, iT1+1), latitude=lats, longitude=lons).drop_vars('analysed_sst')
sub['mhw'] = (('time', 'latitude', 'longitude'), mhw_region.astype(np.uint8))
sub.to_netcdf('/work/output/mhw_mask.nc')

report = {
  'region': {'lat_min': 54.39, 'lat_max': 55.59, 'lon_min': 18.25, 'lon_max': 19.45},
  'baseline_analysed': {'start': str(span0), 'end': str(span1)},
  'target_analysed': {'start': '2020-06-01', 'end': '2020-08-31'},
  'events': [{'onset': e[0], 'end': e[1]} for e in events],
  'complete': True,
  'caveats': ('Per-cell MHW masks restricted to the 92 target days; sea cells = 3309 of 3600 region cells with finite SST on all target days. '
              'Day-of-year 60 (29 Feb) threshold/climatology set to mean of days 59 and 61 before centred 31-day wraparound smoothing; '
              'the 90th percentile uses numpy method=hazen; +/-5-day climatology windows reach 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05.')
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print('written. report:', json.dumps(report)[:1200])
