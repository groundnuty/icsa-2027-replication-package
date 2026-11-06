import numpy as np, datetime as dt, time, warnings
warnings.filterwarnings('ignore')

sst = np.load('/work/sst_cube.npy')      # (4120, 61, 61)
sea = np.load('/work/sea_mask.npy')      # (61, 61)
NB = 4027

CUM = [31,29,31,30,31,30,31,31,30,31,30,31]
def dayofyear(d):
    return sum(CUM[:d.month-1]) + d.day

doys_all = np.array([dayofyear(dt.date(1991,12,27)+dt.timedelta(days=k)) for k in range(NB)])
yrs_all  = np.array([(dt.date(1991,12,27)+dt.timedelta(days=k)).year for k in range(NB)])
base_pos = np.where((yrs_all >= 1992) & (yrs_all <= 2002))[0]
base_doys = doys_all[base_pos]

# flatten sea cells
sea_flat_idx = np.where(sea.ravel())[0]
sst_flat = sst.reshape(sst.shape[0], -1)[:, sea_flat_idx]   # (4120, 3370)
print("sst_flat:", sst_flat.shape)

thr_unsmoothed = np.full((366, sst_flat.shape[1]), np.nan)
clim_unsmoothed = np.full((366, sst_flat.shape[1]), np.nan)

t0 = time.time()
for d in range(1, 367):
    if d == 60:
        continue
    w = (((d - 1 + np.arange(-5, 6)) % 366) + 1)
    idx = base_pos[np.isin(base_doys, w)]
    vals = sst_flat[idx]                       # (n, C)
    thr_unsmoothed[d-1] = np.nanquantile(vals, 0.9, axis=0, method='hazen')
    clim_unsmoothed[d-1] = np.nanmean(vals, axis=0)
print(f"pools done in {time.time()-t0:.1f}s")

# day 60 = mean of days 59 and 61 (before smoothing)
thr_unsmoothed[59] = 0.5*(thr_unsmoothed[58] + thr_unsmoothed[60])
clim_unsmoothed[59] = 0.5*(clim_unsmoothed[58] + clim_unsmoothed[60])
print("day60 filled, any NaN in thr/clim:", np.isnan(thr_unsmoothed).any(), np.isnan(clim_unsmoothed).any())
np.save('/work/thr_unsmoothed.npy', thr_unsmoothed)
np.save('/work/clim_unsmoothed.npy', clim_unsmoothed)
