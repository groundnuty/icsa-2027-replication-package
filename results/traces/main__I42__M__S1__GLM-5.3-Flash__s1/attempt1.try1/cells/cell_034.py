import numpy as np, pickle
from datetime import date, timedelta

thr_smooth2 = np.load("/work/thr_smooth2.npy")
thr_smooth1 = np.load("/work/thr_smooth.npy")
# difference over the target doys (153..244)
diff = thr_smooth2[152:244] - thr_smooth1[152:244]
print("max abs diff over target doys:", np.nanmax(np.abs(diff)))
# where is the max?
i,j,k = np.unravel_index(np.nanargmax(np.abs(diff)), diff.shape)
print("at target day", i, "cell", j, k)
# hot days comparison
sst_t = np.load("/work/sst_target.npy")
MD_CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
target_dates = []
d = date(2012,6,1)
while d <= date(2012,8,31):
    target_dates.append(d); d += timedelta(days=1)
doys = np.array([MD_CUM[t.month-1]+t.day for t in target_dates])
sea_mask = np.isfinite(sst_t).all(axis=0)
with np.errstate(invalid="ignore"):
    hot2 = (sst_t >= thr_smooth2[doys-1]) & sea_mask[None]
    hot1 = (sst_t >= thr_smooth1[doys-1]) & sea_mask[None]
print("hot2 total:", hot2.sum(), "hot1 total:", hot1.sum(), "differing day-cells:", (hot2 != hot1).sum())
