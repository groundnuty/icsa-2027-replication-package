import numpy as np, datetime as dt

sst = np.load('/work/sst_cube.npy')
sea = np.load('/work/sea_mask.npy')
thr_s = np.load('/work/thr_smoothed.npy')
i0, i1 = 4028, 4119
CUM = [31,29,31,30,31,30,31,31,30,31,30,31]
dates_t = [dt.date(2012,6,1)+dt.timedelta(days=k) for k in range(92)]
doys_t = np.array([sum(CUM[:d.month-1])+d.day for d in dates_t])

sea_flat_idx = np.where(sea.ravel())[0]
sst_t = sst[i0:i1+1].reshape(92, -1)[:, sea_flat_idx]

# distribution of per-cell margins (sst - threshold) per day, and how close cells get
margin = sst_t - thr_s[doys_t-1]
print("overall max margin:", margin.max().round(3))
print("fraction of (day,cell) pairs within 1K of threshold:", (margin > -1).mean().round(3))
print("fraction within 0.5K:", (margin > -0.5).mean().round(3))
# per-day 99.9th percentile of margin across cells
for k in range(0, 92, 5):
    print(dates_t[k], "max margin:", round(margin[k].max(),2), " q99:", round(np.quantile(margin[k], 0.99),2))

# warmest August 2012: how high is SST vs the pool's top
# find the cell with hot run (4,38); its Aug 17-19 vs baseline Aug 15-21 values
jr, ic = 4, 38
f = jr*61+ic
c = int(np.where(sea_flat_idx == f)[0][0])
k_aug17 = 77  # Aug 17
vals_pool = None
NB = 4027
dates_all = [dt.date(1991,12,27)+dt.timedelta(days=k) for k in range(NB)]
doys_all = np.array([sum(CUM[:d.month-1])+d.day for d in dates_all])
yrs = np.array([d.year for d in dates_all])
base_pos = np.where((yrs>=1992)&(yrs<=2002))[0]
bdo = doys_all[base_pos]
d = doys_t[77]
w = (((d-1+np.arange(-5,6))%366)+1)
idx = base_pos[np.isin(bdo, w)]
pool = sst[np.ix_(idx, [jr], [ic])][:,0,0]
print("\ncell (4,38) pool Aug ~ (n=%d): mean=%.2f q90=%.2f max=%.2f" % (len(pool), pool.mean(), np.nanquantile(pool,0.9,method='hazen'), pool.max()))
print("2012 values Aug 15-21:", sst[i0+75:i0+82, jr, ic].round(2))
