import numpy as np
hot = np.load("/work/hot.npy") if False else None
# recompute quickly
import pickle
from datetime import date, timedelta
sst_t = np.load("/work/sst_target.npy"); thr_s = np.load("/work/thr_smooth.npy")
MD_CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
target_dates = []
d = date(2012,6,1)
while d <= date(2012,8,31):
    target_dates.append(d); d += timedelta(days=1)
doys = np.array([MD_CUM[t.month-1] + t.day for t in target_dates])
thr_target = thr_s[doys - 1]
with np.errstate(invalid="ignore"):
    hot = (sst_t >= thr_target)
sea_mask = np.isfinite(sst_t).all(axis=0)
hot_finite = hot & sea_mask[None]
nhot_cell = hot_finite.sum(axis=0)
print("max hot days per cell:", nhot_cell.max())
import collections
print("histogram of hot-day counts per cell:", np.bincount(nhot_cell.ravel(), minlength=93)[:20], "...")
# how many cells have >= 5 hot days in a row? approximate: total cells with any run>=5
# do a quick per-cell longest-run computation
def longest_run(mask1d):
    best = 0; cur = 0
    for v in mask1d:
        cur = cur+1 if v else 0
        best = max(best, cur)
    return best
lr = np.zeros((60,60), dtype=int)
for ii in range(60):
    for jj in range(60):
        lr[ii,jj] = longest_run(hot_finite[:,ii,jj])
print("cells with longest run >= 5:", (lr >= 5).sum())
print("max longest run:", lr.max())
print("hist of longest runs (0..10+):", np.bincount(lr.ravel(), minlength=11))
np.save("/work/hot_finite.npy", hot_finite)
