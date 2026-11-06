
import numpy as np, datetime as dt, warnings

z = np.load('work/sst.npz', allow_pickle=True)
days = [dt.date.fromisoformat(x) for x in z['days']]
sst = z['sst']
nbase = 4028
sst_base = sst[:nbase]
day_index = {d: i for i, d in enumerate(days)}

mleap = [31,29,31,30,31,30,31,31,30,31,30,31]
pref = [0]
for m in mleap: pref.append(pref[-1]+m)
def doy(d):
    return pref[d.month-1] + d.day
assert doy(dt.date(2000,1,1))==1 and doy(dt.date(2000,2,28))==59 and doy(dt.date(2000,2,29))==60 and doy(dt.date(2000,3,1))==61 and doy(dt.date(2000,12,31))==366
assert doy(dt.date(1991,12,27))==362 and doy(dt.date(2003,1,5))==5

doy_md = {}
m = 1
for k in range(1, 367):
    while k > pref[m]:
        m += 1
    doy_md[k] = (m, k - pref[m-1])
assert doy_md[60] == (2, 29) and doy_md[61] == (3, 1) and doy_md[366] == (12, 31)

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

thr[59]  = 0.5 * (thr[58] + thr[60])
clim[59] = 0.5 * (clim[58] + clim[60])

def smooth31(a):
    idx = (np.arange(366)[:, None] + np.arange(-15, 16)[None, :]) % 366
    return a[idx].mean(axis=1)

thr_s = smooth31(thr)
clim_s = smooth31(clim)

sst_t = sst[nbase:]
sea = np.all(np.isfinite(sst_t), axis=0)
print('sea cells:', int(sea.sum()), 'of', sea.size)
print('thr_s finite on sea cells (all days):', bool(np.isfinite(thr_s[:, sea]).all()),
      '| clim_s:', bool(np.isfinite(clim_s[:, sea]).all()))
print('thr_s day182 sea min/med/max:', np.nanmin(thr_s[181][sea]), np.nanmedian(thr_s[181][sea]), np.nanmax(thr_s[181][sea]))
print('clim_s day200 med:', np.nanmedian(clim_s[199][sea]))
print('sst target day0 med:', np.nanmedian(sst_t[0][sea]))

np.savez_compressed('work/thrclim.npz', thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s, sea=sea)
print('saved')
