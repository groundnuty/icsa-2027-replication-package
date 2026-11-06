import numpy as np, datetime as dt, warnings

z = np.load('/work/cache_stage1.npz')
base_sst = z['base_sst']
nd, nla, nlo = base_sst.shape
ncell = nla * nlo
base_flat = base_sst.reshape(nd, ncell)
D0 = dt.date(1991, 12, 27)
bdates = [D0 + dt.timedelta(days=i) for i in range(nd)]
row_of = {d: i for i, d in enumerate(bdates)}
def doy_of(d): return (dt.date(2000, d.month, d.day) - dt.date(2000, 1, 1)).days + 1
def md_of_doy(k):
    r = dt.date(2000, 1, 1) + dt.timedelta(days=k - 1); return r.month, r.day

thr_raw = np.full((366, ncell), np.nan)
clim_raw = np.full((366, ncell), np.nan)
for k in range(1, 367):
    if k == 60: continue
    m, dd = md_of_doy(k)
    rows = set()
    for y in range(1992, 2003):
        a = dt.date(y, m, dd)
        for off in range(-5, 6):
            rows.add(row_of[a + dt.timedelta(days=off)])
    rows = np.array(sorted(rows))
    pool = base_flat[rows, :]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        thr_raw[k-1] = np.nanpercentile(pool, 90, axis=0, method='hazen')
        clim_raw[k-1] = np.nanmean(pool, axis=0)

def pool_dates(k):
    m, dd = md_of_doy(k)
    rows = set()
    for y in range(1992, 2003):
        a = dt.date(y, m, dd)
        for off in range(-5, 6):
            rows.add(row_of[a + dt.timedelta(days=off)])
    return sorted(dt.date(1991, 12, 27) + dt.timedelta(days=i) for i in rows)

rp = pool_dates(180)
yrs = sorted(set(d.year for d in rp))
print('doy180: n=%d, years=%s, span %s -> %s' % (len(rp), yrs, min(rp), max(rp)))
assert len(rp) == 121 and yrs == list(range(1992, 2003))
assert min(rp) == dt.date(1992, 6, 19) and max(rp) == dt.date(2002, 7, 4)

thr_raw[59] = 0.5 * (thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5 * (clim_raw[58] + clim_raw[60])
print('day60 NaN:', int(np.isnan(thr_raw[59]).sum()), int(np.isnan(clim_raw[59]).sum()))

offs = np.arange(-15, 16)
idx = (np.arange(366)[:, None] + offs[None, :]) % 366
def smooth(raw):
    acc = np.zeros_like(raw)
    for j in range(31):
        acc += raw[idx[:, j]]
    return acc / 31.0

thr_s = smooth(thr_raw)
clim_s = smooth(clim_raw)
manual = np.mean([thr_raw[(0 + o) % 366, 0] for o in offs])
assert abs(thr_s[0, 0] - manual) < 1e-12
print('smooth check OK: thr_s[day1,cell0]=%.6f' % thr_s[0, 0])
print('NaN thr: %d; NaN clim: %d' % (int(np.isnan(thr_s).sum()), int(np.isnan(clim_s).sum())))
tdoys = np.array([doy_of(dt.date(2008, 6, 1) + dt.timedelta(days=i)) for i in range(92)])
print('target doys %d..%d; NaN thr in target doys: %d' % (tdoys.min(), tdoys.max(), int(np.isnan(thr_s[tdoys-1]).sum())))
sea = z['sea'].reshape(-1)
c = int(np.argmax(sea))
print('sample cell: thr_sm[180]=%.3f clim_sm[180]=%.3f K' % (thr_s[179, c], clim_s[179, c]))
np.savez('/work/cache_stage2.npz', thr_s=thr_s, clim_s=clim_s, tdoys=tdoys, sea=sea)
print('stage2 saved')
