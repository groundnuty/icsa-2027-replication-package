import numpy as np, datetime as dt

sst = np.load('/work/sst_cube.npy')
sea = np.load('/work/sea_mask.npy')
thr_s = np.load('/work/thr_smoothed.npy')
thr_u = np.load('/work/thr_unsmoothed.npy')
i0, i1 = 4028, 4119

CUM = [31,29,31,30,31,30,31,31,30,31,30,31]
dates_t = [dt.date(2012,6,1)+dt.timedelta(days=k) for k in range(92)]
doys_t = np.array([sum(CUM[:d.month-1])+d.day for d in dates_t])

sea_flat_idx = np.where(sea.ravel())[0]
sst_t = sst[i0:i1+1].reshape(92, -1)[:, sea_flat_idx]
hot = sst_t >= thr_s[doys_t-1]

kk, cc = np.where(hot)
print("hot cell-days (day, cell, sst, thr):")
for k, c in zip(kk, cc):
    f = sea_flat_idx[c]
    jr, ic = divmod(int(f), 61)
    print(dates_t[int(k)], "cell2D", (jr, ic), "sst=", round(sst_t[k, c],3), "thr_s=", round(thr_s[doys_t[k]-1, c],3), "thr_u=", round(thr_u[doys_t[k]-1, c],3))

# per-day counts
counts = hot.sum(axis=1)
nz = np.where(counts > 0)[0]
print("\ndays with any hot cells:", [(str(dates_t[int(k)]), int(counts[k])) for k in nz])
# check max consecutive hot days in any cell
def max_run(h):
    best = 0; cur = 0
    for v in h:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best
mr = max(max_run(hot[:, c]) for c in range(hot.shape[1]))
print("max run length of consecutive hot days in any single cell:", mr)
