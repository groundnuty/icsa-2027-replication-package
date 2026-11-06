import numpy as np, datetime as dt

z = np.load('mhw_cache.npz', allow_pickle=False)
tgt_data = z['tgt_data'].astype(np.float64)
c = np.load('clim_thr.npz'); thr_s = c['thr']; clm_s = c['clm']

def doy366(d):
    cum = [0,31,59,90,120,151,181,212,243,273,304,334]
    if d.month==2 and d.day==29: return 60
    v = cum[d.month-1]+d.day
    return v+1 if d.month>=3 else v

tgt_days = [dt.date(2004,6,1)+dt.timedelta(days=k) for k in range(tgt_data.shape[0])]
tgt_doy = np.array([doy366(d) for d in tgt_days])
sea = np.isfinite(tgt_data).all(axis=0)

diff = tgt_data - thr_s[tgt_doy-1]          # SST minus threshold
dm = diff[:, sea]
print("SST-threshold over sea cells: min %.2f  p50 %.2f  p90 %.2f  p99 %.2f  max %.3f" %
      (np.nanmin(dm), np.nanpercentile(dm,50), np.nanpercentile(dm,90), np.nanpercentile(dm,99), np.nanmax(dm)))
hot = diff >= 0
print("hot day-cells:", int(np.nansum(hot[:,sea])))
hd = [str(tgt_days[k]) for k in range(tgt_data.shape[0]) if hot[k,sea].any()]
print("days with any hot sea cell:", hd)
anom = tgt_data - clm_s[tgt_doy-1]
print("SST anomaly vs smoothed climatology: mean %.2f K, max %.2f K, p99 %.2f K" %
      (np.nanmean(anom[:,sea]), np.nanmax(anom), np.nanpercentile(anom[:,sea],99)))
# warmest day margin per day
dmax = np.nanmax(diff[:,sea], axis=1)
for k in [0, 30, 61, 91]:
    print(f"  {tgt_days[k]} max(SST-thr) = {dmax[k]:+.3f} K")
