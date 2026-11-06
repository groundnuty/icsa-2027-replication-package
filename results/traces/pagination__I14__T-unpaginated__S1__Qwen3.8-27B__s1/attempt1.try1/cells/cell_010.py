
import numpy as np, datetime as dt, warnings

z = np.load('work/sst.npz', allow_pickle=True)
days = [dt.date.fromisoformat(x) for x in z['days']]
sst = z['sst']                     # (4120,60,60) float64
nbase = 4028
sst_base = sst[:nbase]
day_index = {d: i for i, d in enumerate(days)}

# day-of-year mapping by month/day on leap-year calendar (Jan1=1, Feb28=59, Feb29=60, Mar1=61, Dec31=366)
mleap = [31,29,31,30,31,30,31,31,30,31,30,31]
cum = np.cumsum(mleap)
def doy_of(d):
    return int(cum[d.month-1]) - (mleap[d.month-1] if d.month>1 else 0) - (dt.date(d.year,1,1).toordinal() and 0) + d.day if False else int(np.cumsum([mleap[:d.month]]).sum()) + d.day
# simpler: prefix sums
pref = [0]
for m in mleap: pref.append(pref[-1]+m)
def doy(d):
    return pref[d.month-1] + d.day
# sanity
assert doy(dt.date(2000,1,1))==1 and doy(dt.date(2000,2,28))==59 and doy(dt.date(2000,2,29))==60 and doy(dt.date(2000,3,1))==61 and doy(dt.date(2000,12,31))==366
assert doy(dt.date(1991,12,27))==365 and doy(dt.date(2003,1,5))==5

# month/day for each doy in leap calendar
doy_md = {}
m = 1
d = 1
k = 1
for k in range(1, 367):
    if k > pref[m]:
        m += 1
        d = 1
    else:
        d = k - pref[m-1]
    doy_md[k] = (m, d)

thr = np.full((366, 60, 60), np.nan)
clim = np.full((366, 60, 60), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter('ignore', category=RuntimeWarning)
    for k in range(1, 367):
        if k == 60:
            continue
        m, d = doy_md[k]
        idxs = []
        for y in range(1992, 2003):
            b = dt.date(y, m, d)
            idxs += [day_index[b] + off for off in range(-5, 6)]
        idxs = np.array(idxs)
        pool = sst_base[idxs]                      # (121,60,60)
        clim[k-1] = np.nanmean(pool, axis=0)
        thr[k-1]  = np.nanquantile(pool, 0.9, axis=0, method='hazen')

# day 60 = mean of days 59 and 61 (arrays are 0-based: idx 58, 59, 60)
thr[59]  = 0.5 * (thr[58] + thr[60])
clim[59] = 0.5 * (clim[58] + clim[60])

def smooth31(a):
    idx = (np.arange(366)[:, None] + np.arange(-15, 16)[None, :]) % 366
    return a[idx].mean(axis=1)

thr_s = smooth31(thr)
clim_s = smooth31(clim)

print('thr_s finite frac:', np.isfinite(thr_s).mean().round(4))
print('clim_s finite frac:', np.isfinite(clim_s).mean().round(4))
# sea cells (finite on all target days)
sst_t = sst[nbase:]
sea = np.all(np.isfinite(sst_t), axis=0)
print('sea cells:', sea.sum(), 'of', sea.size)
thr_sea = thr_s[:, sea]
print('threshold finite on sea cells:', np.isfinite(thr_sea).all(),
      'clim finite:', np.isfinite(clim_s[:, sea]).all())
print('sample thr_s day182 (Jun 1) sea cells min/med/max:',
      np.nanmin(thr_s[181]), np.nanmedian(thr_s[181][sea]), np.nanmax(thr_s[181][sea]))
print('sample clim_s day200:', np.nanmedian(clim_s[199][sea]))

np.savez_compressed('work/thrclim.npz', thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s, sea=sea)
print('saved')
