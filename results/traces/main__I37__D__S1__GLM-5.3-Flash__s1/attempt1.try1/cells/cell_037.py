import numpy as np, datetime as dt

sst = np.load('/work/sst_cube.npy')
sea = np.load('/work/sea_mask.npy')
thr_u = np.load('/work/thr_unsmoothed.npy')
clim_u = np.load('/work/clim_unsmoothed.npy')
NB = 4027

CUM = [31,29,31,30,31,30,31,31,30,31,30,31]
def dayofyear(d):
    return sum(CUM[:d.month-1]) + d.day

dates_all = [dt.date(1991,12,27)+dt.timedelta(days=k) for k in range(NB)]
doys_all = np.array([dayofyear(d) for d in dates_all])
yrs_all = np.array([d.year for d in dates_all])
base_pos = np.where((yrs_all>=1992)&(yrs_all<=2002))[0]
base_doys = doys_all[base_pos]

sea_flat_idx = np.where(sea.ravel())[0]

# pick doy 213 (Aug 1) and a mid-region sea cell
d = 213
w = (((d-1+np.arange(-5,6)) % 366) + 1)
idx = base_pos[np.isin(base_doys, w)]
cell = len(sea_flat_idx)//2
vals = sst[np.ix_(idx, np.array([cell]))][:,0]
vals = sst[idx][:, sea_flat_idx[cell]]
print("pool size:", len(vals))
print("pool mean:", np.nanmean(vals).round(3), "std:", np.nanstd(vals).round(3))
print("hazen q90:", np.nanquantile(vals, 0.9, method='hazen').round(3))
print("linear q90:", np.nanquantile(vals, 0.9, method='linear').round(3))
print("thr_u[212,cell]:", thr_u[212, cell].round(3), "clim_u[212,cell]:", clim_u[212, cell].round(3))
sv = np.sort(vals[~np.isnan(vals)])
print("sorted pool around 90th pct (n=%d):" % len(sv), sv[int(len(sv)*0.85):int(len(sv)*0.93)].round(2))
# year-to-year spread: value at Aug 1 each year for this cell
for y in range(1992, 2003):
    k = dates_all.index(dt.date(y,8,1))
    print(y, round(sst[k, sea_flat_idx[0]+cell-sea_flat_idx[cell]] if False else sst[k].reshape(-1)[sea_flat_idx[cell]],2))
