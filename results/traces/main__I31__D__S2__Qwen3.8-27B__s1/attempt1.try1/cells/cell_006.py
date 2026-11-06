import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

D = np.load('/work/region_data.npz')
base = D['base']; tgt = D['tgt']
t_base = D['t_base']; t_tgt = D['t_tgt']
Tb = len(t_base)

# fixed (month,day) -> day-of-year mapping: Jan1=1, Feb28=59, Feb29=60, Mar1=61 ... Dec31=366
mdays = np.array([31,28,31,30,31,30,31,31,30,31,30,31])
cum = np.concatenate([[0], np.cumsum(mdays)])
def doy_of(strs):
    m = np.array([int(s[5:7]) for s in strs]); d = np.array([int(s[8:10]) for s in strs])
    doy = cum[m-1] + d
    doy[(m == 2) & (d == 29)] = 60
    return doy
doyb = doy_of(t_base)
doyt = doy_of(t_tgt)
print("target doys:", doyt.min(), doyt.max(), "unique count", len(set(doyt.tolist())), "has 60?", 60 in set(doyt.tolist()))

in_base = (t_base >= "1992-01-01") & (t_base <= "2002-12-31")
print("baseline anchor days:", in_base.sum(), t_base[in_base][0], t_base[in_base][-1])

thr = np.full((366, 3600), np.nan); clim = np.full((366, 3600), np.nan)
sizes = set()
for dd in range(1, 367):
    if dd == 60:
        continue
    idx = np.where((doyb == dd) & in_base)[0]
    pool = np.concatenate([base[i-5:i+6] for i in idx])
    sizes.add(pool.shape[0])
    vals = pool.reshape(pool.shape[0], 3600)
    thr[dd-1] = np.nanquantile(vals, 0.90, axis=0, method='hazen')
    clim[dd-1] = np.nanmean(vals, axis=0)
print("pool sizes per doy:", sizes)

# fill day 60 (index 59) with mean of 59 and 61 (indices 58, 60)
thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0

# 31-day centred wrap-around moving mean over the 366-element arrays
def smooth366(a):
    pad = np.concatenate([a[-15:], a, a[:15]])
    return sliding_window_view(pad, 31).mean(axis=1)
thr_s = smooth366(thr); clim_s = smooth366(clim)

# sea cells: finite on every target day
sea = np.isfinite(tgt).all(axis=0)
print("sea cells:", sea.sum(), "of", 3600)
ns = int(sea.sum())
print("thr_s finite for sea cells all doys:", bool(np.isfinite(thr_s[:, sea]).all()))

# sanity: thresholds for target doys in deg C
sub = thr_s[doyt-1][:, sea]
print("smoothed thr during Jun-Aug (degC): min %.3f med %.3f max %.3f" % (
    (sub.min()-273.15), np.median(sub-273.15), (sub.max()-273.15)))
print("tgt SST (degC): min %.3f med %.3f max %.3f" % (
    np.nanmin(tgt[:,sea]-273.15), np.nanmedian(tgt[:,sea]-273.15), np.nanmax(tgt[:,sea]-273.15)))

np.savez_compressed('/work/intermediate.npz',
    thr_s=thr_s, clim_s=clim_s, sea=sea, doyt=doyt,
    t_tgt=t_tgt, lat=D['lat'], lon=D['lon'])
print("intermediates saved")
