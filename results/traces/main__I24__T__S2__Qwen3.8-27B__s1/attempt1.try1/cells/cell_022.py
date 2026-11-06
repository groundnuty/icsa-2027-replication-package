import numpy as np, xarray as xr, json

sub = xr.open_dataset("/tmp/mhw/subset.nc")
sst = sub.analysed_sst.values
ts = sub.time.values.astype("datetime64[D]")
o = (ts - ts.astype("datetime64[Y]")).astype("timedelta64[D]").astype(np.int64) + 1
year = ts.astype("datetime64[Y]").astype(np.int64) + 1970
is_leap = (year % 4 == 0) & ((year % 100 != 0) | (year % 400 == 0))
doy = o + np.where(~is_leap & (o > 59), 1, 0)

thr_s = np.load("/tmp/mhw/thr_s.npy")
clim_s = np.load("/tmp/mhw/clim_s.npy")
mask = np.load("/tmp/mhw/mask.npy")
sea = np.load("/tmp/mhw/sea.npy")

T0 = 4028
tt = sst[T0:]; tt_times = ts[T0:]; doys_t = doy[T0:]

active = mask.any(axis=2).any(axis=1)
nonact_cum = np.cumsum(~active)
lab = nonact_cum[active]
events = []
for v in np.unique(lab):
    days = np.where(active & (nonact_cum == v))[0]
    events.append((days.min(), days.max()))
print("independent events:", [(str(tt_times[a].astype('datetime64[D]')), str(tt_times[b].astype('datetime64[D]'))) for a, b in events])
ok = True
for k in range(len(events)-1):
    g = slice(events[k][1]+1, events[k+1][0])
    if active[g].any() or events[k+1][0] - events[k][1] != 1:
        ok = False
print("maximal & consecutive:", ok)
assert ok

fin_target = np.isfinite(tt).all(axis=0)
excl = ~fin_target
print("excluded:", int(excl.sum()), "| fully NaN over target:", int((np.isfinite(tt).sum(axis=0)==0).sum()),
      "| partially finite:", int(((np.isfinite(tt).sum(axis=0)>0) & excl).sum()))
fin_base = np.isfinite(sst[:T0]).mean(axis=0)
print("excluded cells with any baseline data:", int((fin_base[excl] > 0).sum()))

e0, e1 = events[0]
an = tt - clim_s[doys_t - 1]
dev = tt - thr_s[doys_t - 1]
ev_an = an[e0:e1+1][:, sea]
ev_dev = dev[e0:e1+1][:, sea]
print("event %s..%s len=%d" % (str(tt_times[e0].astype('datetime64[D]')), str(tt_times[e1].astype('datetime64[D]')), e1-e0+1))
print("event SST anomaly vs climatology: min %.2f mean %.2f max %.2f" % (ev_an.min(), ev_an.mean(), ev_an.max()))
print("event excess over threshold: mean %.3f max %.3f" % (ev_dev.mean(), ev_dev.max()))
peak = int(ev_dev.argmax())
t = peak // ev_dev.shape[1]; c = peak % ev_dev.shape[1]
flat_sea = np.where(sea.ravel())[0]
ii = int(flat_sea[c])
print("peak: day", str(tt_times[t].astype('datetime64[D]')), "lat/lon",
      sub.latitude.values[ii//60], sub.longitude.values[ii%60],
      "SST %.2f thr %.2f clim %.2f" % (tt[t, ii//60, ii%60], thr_s[doys_t[t]-1, ii//60, ii%60], clim_s[doys_t[t]-1, ii//60, ii%60]))
for t in range(63, 78):
    print(str(tt_times[t].astype('datetime64[D]')), int(mask[t].sum()))
