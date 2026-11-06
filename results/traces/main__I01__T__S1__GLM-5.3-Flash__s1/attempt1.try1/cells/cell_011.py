import numpy as np, datetime as dt, warnings, json

z = np.load('/work/cache_stage1.npz')
base_sst = z['base_sst']            # (4028, 60, 60) float64
tgt_sst  = z['tgt_sst']             # (92, 60, 60) float64
lat_r, lon_r = z['lat_r'], z['lon_r']
nd, nla, nlo = base_sst.shape
ncell = nla*nlo
base_flat = base_sst.reshape(nd, ncell)
tgt_flat  = tgt_sst.reshape(92, ncell)

D0 = dt.date(1991,12,27)
bdates = [D0 + dt.timedelta(days=i) for i in range(nd)]
row_of = {d: i for i, d in enumerate(bdates)}

def doy_of(d):   # month/day -> doy 1..366 (leap-year frame)
    return (dt.date(2000, d.month, d.day) - dt.date(2000,1,1)).days + 1
def md_of_doy(k):  # doy -> (month, day) using leap year 2000
    r = dt.date(2000,1,1) + dt.timedelta(days=k-1)
    return r.month, r.day

# checks of the doy mapping
for dstr, exp in [('1991-12-27',361),('1992-01-01',1),('1992-02-28',59),('1992-02-29',60),
                  ('1992-03-01',61),('1993-02-28',59),('1993-03-01',61),('1996-12-31',366),
                  ('2001-12-31',366),('2002-12-31',366),('2008-06-01',153),('2008-08-31',244)]:
    y,m,dd = map(int, dstr.split('-'))
    got = doy_of(dt.date(y,m,dd))
    assert got == exp, (dstr, got, exp)
print('doy mapping checks OK')

thr_raw = np.full((366, ncell), np.nan)
clim_raw = np.full((366, ncell), np.nan)
feb29_rows = [row_of(dt.date(y,2,29)) for y in (1992,1996,2000)]
pool_sizes = []
for k in range(1, 367):
    if k == 60:
        continue
    m, dd = md_of_doy(k)
    rows = set()
    for y in range(1992, 2003):
        a = dt.date(y, m, dd)
        for off in range(-5, 6):
            t = a + dt.timedelta(days=off)
            rows.add(row_of[t])
    pool_sizes.append(len(rows))
    rows = np.array(sorted(rows))
    pool = base_flat[rows, :]                      # (121, ncell) float64
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        thr_raw[k-1]  = np.nanpercentile(pool, 90, axis=0, method='hazen')
        clim_raw[k-1] = np.nanmean(pool, axis=0)
pool_sizes = np.array(pool_sizes)
print('pool sizes: min %d max %d (expect 121)' % (pool_sizes.min(), pool_sizes.max()))

# boundary window checks
def rows_for_doy(k):
    m, dd = md_of_doy(k); rows = set()
    for y in range(1992, 2003):
        a = dt.date(y, m, dd)
        for off in range(-5,6): rows.add(row_of[a+dt.timedelta(days=off)])
    return rows
r1 = rows_for_doy(1);  assert all(row_of[dt.date(1991,12,d)] in r1 for d in range(27,32))
assert row_of[dt.date(1991,12,26)] not in r1
r366 = rows_for_doy(366); assert all(row_of[dt.date(2003,1,d)] in r366 for d in range(1,6))
assert row_of[dt.date(2003,1,6)] not in r366
r61 = rows_for_doy(61);  assert all(r in r61 for r in feb29_rows)   # 1 Mar window reaches 29 Feb
r65 = rows_for_doy(65);  assert all(r in r65 for r in feb29_rows)   # 5 Mar: 29 Feb exactly 5 days before
r66 = rows_for_doy(66);  assert not any(r in r66 for r in feb29_rows)
r55 = rows_for_doy(55);  assert all(r in r55 for r in feb29_rows)   # 24 Feb +5 = 29 Feb
r54 = rows_for_doy(54);  assert not any(r in r54 for r in feb29_rows)
print('boundary / 29-Feb window checks OK')

# day 60 fill (raw, pre-smoothing)
thr_raw[59]  = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])
print('day60 NaN in thr/clim:', int(np.isnan(thr_raw[59]).sum()), int(np.isnan(clim_raw[59]).sum()))

# cyclic 31-day centred moving mean (unweighted, wrap over 366)
offs = np.arange(-15, 16)
idx = (np.arange(366)[:, None] + offs[None, :]) % 366     # (366, 31)
def smooth(raw):
    acc = np.zeros_like(raw)
    for j in range(31):
        acc += raw[idx[:, j]]
    return acc / 31.0
thr_s = smooth(thr_raw)
clim_s = smooth(clim_raw)

# verify smoothing by hand for one element (day 1, cell 0)
manual = np.mean([thr_raw[(0+o) % 366, 0] for o in offs])
print('smooth check day1 cell0: %.6f vs %.6f' % (thr_s[0,0], manual))
assert abs(thr_s[0,0]-manual) < 1e-12

print('NaN thresholds total: %d; NaN clim total: %d' % (int(np.isnan(thr_s).sum()), int(np.isnan(clim_s).sum())))
tdoys = np.array([doy_of(dt.date(2008,6,1)+dt.timedelta(days=i)) for i in range(92)])
print('target doys: %d..%d' % (tdoys.min(), tdoys.max()))
print('NaN thr in target doys:', int(np.isnan(thr_s[tdoys-1]).sum()))

# plausibility: sample sea cell, a few doys
sea = z['sea'].reshape(-1)
c = int(np.argmax(sea))
for k in [1, 60, 120, 180, 244, 366]:
    fin = base_flat[:, c]
    print('doy %3d: thr_raw %.3f thr_sm %.3f clim_sm %.3f' % (k, thr_raw[k-1,c], thr_s[k-1,c], clim_s[k-1,c]))
np.savez('/work/cache_stage2.npz', thr_s=thr_s, clim_s=clim_s, tdoys=tdoys, sea=sea)
print('stage2 saved')
