import numpy as np, datetime as dt, json, os, time, warnings

t0 = time.time()
ext = np.load('cache/ext.npy')          # (4028, 60, 60) 1991-12-27..2003-01-05
meta = json.load(open('cache/meta.json'))
dates_ext = [dt.date.fromisoformat(s) for s in meta['dates_ext']]
assert ext.shape[0] == len(dates_ext)
date_index = {d: i for i, d in enumerate(dates_ext)}
B0, B1 = dt.date(1992,1,1), dt.date(2002,12,31)

# month/day -> day-of-year (1..366), Feb 29 -> 60, Mar 1 -> 61, Dec 31 -> 366
cum = np.concatenate([[0], np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])])
def md_doy(d):
    return int(cum[d.month-1] + d.day)
assert md_doy(dt.date(2020,2,28))==59 and md_doy(dt.date(2020,2,29))==60
assert md_doy(dt.date(2020,3,1))==61 and md_doy(dt.date(2021,12,31))==366
assert md_doy(dt.date(2021,6,1))==153 and md_doy(dt.date(2021,8,31))==244

# pool index lists: pool[d] = indices of ext days belonging to day-of-year d
pool_idx = {d: [] for d in range(1, 367) if d != 60}
for i, x in enumerate(dates_ext):
    for o in range(-5, 6):
        z = x + dt.timedelta(days=o)
        if B0 <= z <= B1 and not (z.month == 2 and z.day == 29):
            pool_idx[md_doy(z)].append(i)

sizes = {d: len(v) for d, v in pool_idx.items()}
print('pool sizes: min', min(sizes.values()), 'max', max(sizes.values()),
      '| days with size 121:', sum(1 for v in sizes.values() if v == 121))
# spot checks
def dates_of(idxs): return [dates_ext[i].isoformat() for i in idxs]
print('pool[1] first/last:', dates_of(pool_idx[1])[:6], '...', dates_of(pool_idx[1])[-6:])
print('pool[366] first/last:', dates_of(pool_idx[366])[:6], '...', dates_of(pool_idx[366])[-6:])
p56 = dates_of(pool_idx[56])
print('pool[56] unique:', sorted(set(p56))[:12])
print('  contains 1992-02-29:', '1992-02-29' in p56, '| 1996-02-29:', '1996-02-29' in p56,
      '| 1993-03-02:', '1993-03-02' in p56, '| 1992-03-02:', '1992-03-02' in p56)
print('  contains 1993-03-03 (should be False):', '1993-03-03' in p56)
p153 = dates_of(pool_idx[153])
print('pool[153] for 1992:', [x for x in p153 if x.startswith('1992')])

NT, NY, NX = ext.shape[1], ext.shape[2], ext.shape[3]
raw_thresh = np.full((366, NY, NX), np.nan)
raw_clim   = np.full((366, NY, NX), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter('ignore', RuntimeWarning)  # all-NaN slices (land cells)
    for d in range(1, 367):
        if d == 60:
            continue
        pool = ext[np.asarray(pool_idx[d])]           # (n, 60, 60) float64
        raw_thresh[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        raw_clim[d-1]   = np.nanmean(pool, axis=0)
print('pools done %.1f s' % (time.time()-t0))

# day 60 <- mean of days 59 and 61 (raw), then centred 31-day circular moving mean
for arr in (raw_thresh, raw_clim):
    arr[59] = 0.5 * (arr[58] + arr[60])

def circ_smooth31(a):  # a: (366, ...) -> centred 31-day unweighted moving mean, mod 366
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.cumsum(pad, axis=0)
    c = np.concatenate([np.zeros_like(c[:1]), c], axis=0)
    return (c[31:] - c[:-31]) / 31.0     # window padded[i-? ] check below

# verify cumsum windowing: smoothed[i] = mean(padded[i:i+31])
sm_t = circ_smooth31(raw_thresh)
sm_c = circ_smooth31(raw_clim)
# manual check for a few indices
for i in [0, 1, 59, 182, 365]:
    pad = np.concatenate([raw_thresh[-15:], raw_thresh, raw_thresh[:15]], axis=0)
    m = pad[i:i+31].mean(axis=0)
    assert np.array_equal(m, sm_t[i]), i
print('smoothing verified; day1 window = days 352..366,1..16 ->', sm_t[0] is not None)
np.save('cache/raw_thresh.npy', raw_thresh); np.save('cache/raw_clim.npy', raw_clim)
np.save('cache/sm_thresh.npy', sm_t); np.save('cache/sm_clim.npy', sm_c)

# diagnostics on sea cells
meta_lat = np.array(meta['lat']); meta_lon = np.array(meta['lon'])
tgt = np.load('cache/tgt.npy')
sea = np.isfinite(tgt).all(axis=0)
print('sea cells:', int(sea.sum()))
d153, d200, d244 = sm_t[152], sm_t[199], sm_t[243]
print('smoothed threshold [K] over sea cells: Jun1 mean %.3f | Jul20 mean %.3f | Aug31 mean %.3f'
      % (d153[sea].mean(), d200[sea].mean(), d244[sea].mean()))
print('raw (unsmoothed) threshold Jul20 mean %.3f | clim Jul20 mean %.3f'
      % (raw_thresh[199][sea].mean(), raw_clim[199][sea].mean()))
print('clim smoothed Aug31 mean %.3f' % sm_c[243][sea].mean())
print('total %.1f s' % (time.time()-t0))
