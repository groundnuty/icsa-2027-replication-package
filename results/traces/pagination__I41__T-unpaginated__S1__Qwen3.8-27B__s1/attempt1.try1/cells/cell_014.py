import numpy as np
from datetime import date, timedelta

dat = np.load('/tmp/sst_data.npz')
master = dat['master']; target = dat['target']
lat_r, lon_r = dat['lat_region'], dat['lon_region']
base_dates = [date(1991,12,27)+timedelta(days=i) for i in range(4028)]
base_all   = [date(1992,1,1)+timedelta(days=i) for i in range(4018)]
mdays=[31,29,31,30,31,30,31,31,30,31,30,31]; cum=[0]
for m in mdays: cum.append(cum[-1]+m)
doyf = lambda m,dd: cum[m-1]+dd

ci = 1632
i,k = np.unravel_index(ci,(60,60))
print("cell 1632 -> region lat idx",i,"lon idx",k, "lat,lon:", lat_r[i], lon_r[k])
print("cell column min/max over full master span: %.2f .. %.2f" % (np.nanmin(master[:,i,k]), np.nanmax(master[:,i,k])))

dd = 197
b = [x for x in base_all if doyf(x.month,x.day)==dd]
pool = sorted(set(t for bb in b for off in range(-5,6)
                  for t in [bb+timedelta(days=off)]
                  if date(1991,12,27) <= t <= date(2003,1,5)))
print("pool: n=%d, %s .. %s" % (len(pool), pool[0], pool[-1]))
idx = np.array([(t-base_dates[0]).days for t in pool])
vals = master[idx, i, k]
print("pool vals: n_finite=%d min=%.2f max=%.2f mean=%.3f" % (np.isfinite(vals).sum(), np.nanmin(vals), np.nanmax(vals), np.nanmean(vals)))
print("hazen p90 = %.4f, linear p90 = %.4f" % (np.nanquantile(vals,0.9,method='hazen'), np.nanquantile(vals,0.9,method='linear')))

d2 = np.load('/tmp/mhw_stage2.npz')
sea_cells = d2['sea_cells']; T = d2['T']; thrs = d2['thrs']
j = int(np.where((sea_cells[:,0]==i)&(sea_cells[:,1]==k))[0][0])
print("pipeline j:", j, "T[44,j] (2021-07-15):", T[44,j])
print("thrs[190:205,j] (smoothed):", thrs[190:205, j].round(2))
print("T[40:49,j]:", T[40:49, j].round(2))
sea_mask = np.isfinite(target).all(axis=0)
print("sea_cells identical:", np.array_equal(np.argwhere(sea_mask), sea_cells))
blk = master[idx, i, k]
print("recomputed raw thr[197,j]:", np.nanquantile(blk,0.9,method='hazen'), " saved thrs[197,j]:", thrs[197,j])
print("saved keys:", [k2 for k2 in d2.files])
