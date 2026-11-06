import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
import warnings
warnings.filterwarnings("ignore")

D = np.load('/work/region_data.npz')
base = D['base']; tgt = D['tgt']
t_base = D['t_base']; t_tgt = D['t_tgt']

cum = np.concatenate([[0], np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])])
def doy_of(strs):
    m = np.array([int(s[5:7]) for s in strs]); d = np.array([int(s[8:10]) for s in strs])
    return cum[m-1] + d
doyb = doy_of(t_base); doyt = doy_of(t_tgt)
in_base = (t_base >= "1992-01-01") & (t_base <= "2002-12-31")

thr = np.full((366, 3600), np.nan); clim = np.full((366, 3600), np.nan)
for dd in range(1, 367):
    if dd == 60:
        continue
    idx = np.where((doyb == dd) & in_base)[0]
    pool = np.concatenate([base[i-5:i+6] for i in idx]).reshape(121, 3600)
    thr[dd-1] = np.nanquantile(pool, 0.90, axis=0, method='hazen')
    clim[dd-1] = np.nanmean(pool, axis=0)
thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0

def smooth366(a):
    pad = np.concatenate([a[-15:], a, a[:15]])
    return sliding_window_view(pad, 31, axis=0).mean(axis=1)
thr_s = smooth366(thr); clim_s = smooth366(clim)

sea = np.isfinite(tgt).all(axis=0)
ns = int(sea.sum())
print("sea cells:", ns, "of", 3600)
bad_thr = (~np.isfinite(thr_s[:, sea])).sum()
bad_clim = (~np.isfinite(clim_s[:, sea])).sum()
print("non-finite thr_s values among sea cells/days:", bad_thr, "| clim_s:", bad_clim)
# raw (unsmoothed) NaN count among sea cells
print("raw thr NaN among sea cells:", (~np.isfinite(thr[:, sea])).sum())

sub = thr_s[doyt-1][:, sea]
print("smoothed thr Jun-Aug (degC): min %.3f med %.3f max %.3f" % (
    sub.min()-273.15, np.median(sub-273.15), sub.max()-273.15))
print("tgt SST Jun-Aug (degC): min %.3f med %.3f max %.3f" % (
    np.nanmin(tgt[:,sea]-273.15), np.nanmedian(tgt[:,sea]-273.15), np.nanmax(tgt[:,sea]-273.15)))

np.savez_compressed('/work/intermediate.npz',
    thr_s=thr_s, clim_s=clim_s, sea=sea, doyt=doyt,
    t_tgt=t_tgt, lat=D['lat'], lon=D['lon'])
print("intermediates saved")
