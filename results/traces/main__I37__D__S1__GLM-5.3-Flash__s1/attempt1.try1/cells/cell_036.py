import numpy as np, datetime as dt

sst = np.load('/work/sst_cube.npy')
sea = np.load('/work/sea_mask.npy')
thr_s = np.load('/work/thr_smoothed.npy')
clim_s = np.load('/work/clim_smoothed.npy')
i0, i1 = 4028, 4119
sea_flat_idx = np.where(sea.ravel())[0]
sst_t = sst[i0:i1+1].reshape(92, -1)[:, sea_flat_idx]

CUM = [31,29,31,30,31,30,31,31,30,31,30,31]
dates_t = [dt.date(2012,6,1)+dt.timedelta(days=k) for k in range(92)]
doys_t = np.array([sum(CUM[:d.month-1])+d.day for d in dates_t])

clim_t = clim_s[doys_t-1]
thr_t = thr_s[doys_t-1]
anom = sst_t - clim_t
print("daily regional mean anomaly (SST - clim):")
for k in range(0, 92, 7):
    print(dates_t[k], f"mean_sst={sst_t[k].mean():.2f} clim={clim_t[k].mean():.2f} anom={anom[k].mean():+.2f} thr={thr_t[k].mean():.2f}")
print()
print("overall mean anomaly:", anom.mean().round(3))
print("max daily mean anomaly:", anom.mean(axis=1).max().round(3), "on", dates_t[int(anom.mean(axis=1).argmax())])
print("hot threshold exceedances:", int((sst_t >= thr_t).sum()), "cell-days")

# also check unsmoothed thr vs smoothed for peak
thr_u = np.load('/work/thr_unsmoothed.npy')
print("\nunsmoothed thr doy 213 (cell 0):", thr_u[212,0], "smoothed:", thr_s[212,0])
print("unsmoothed clim doy 213 (cell 0):", np.load('/work/clim_unsmoothed.npy')[212,0], "smoothed:", clim_s[212,0])
