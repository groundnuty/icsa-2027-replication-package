
import numpy as np, datetime as dt
hot = np.load('/tmp/hot.npy'); sea = np.load('/tmp/sea.npy'); mhwA = np.load('/tmp/mhwA.npy')
tor = np.load('/tmp/tdates.npy')
t_doy = np.load('/tmp/t_doy.npy')
thr_s = np.load('/tmp/thr_s.npy'); clim_s = np.load('/tmp/clim_s.npy')
sst_tgt = np.load('/tmp/sst_tgt.npy')

days = [dt.date.fromordinal(int(o)) for o in tor]
per_day_hot = hot[:, sea].sum(axis=1)
per_day_mhw = mhwA[:, sea].sum(axis=1)
print("day        hot  mhw")
for i,d in enumerate(days):
    mark = " <== active" if per_day_mhw[i]>0 else ""
    if i%7==0 or per_day_mhw[i]>0 or per_day_hot[i]>200:
        print(d, f"{per_day_hot[i]:5d} {per_day_mhw[i]:5d}{mark}")

# sample cells
c = 1500
print("\nsample cell", c, "lat~57.58+?", "hot/MHW pattern (92 days):")
print("hot:", hot[:,c].astype(int).tolist())
print("mhw:", mhwA[:,c].astype(int).tolist())
print("sst first 20:", np.round(sst_tgt[:20,c],2).tolist())
print("thr first 20:", np.round(thr_s[t_doy[:20]-1,c],2).tolist())
print("clim first 20:", np.round(clim_s[t_doy[:20]-1,c],2).tolist())

# threshold - climatology typical spread over target doys
diff = (thr_s - clim_s)[t_doy-1]
print("\nthr - clim: min %.3f med %.3f max %.3f K" % (np.nanmin(diff), np.nanmedian(diff), np.nanmax(diff)))
