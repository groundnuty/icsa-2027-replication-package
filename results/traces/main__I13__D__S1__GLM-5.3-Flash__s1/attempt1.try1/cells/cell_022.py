import numpy as np, datetime as dt

datestrs = np.load('/work/extract_dates.npy')
arr32 = np.load('/work/extract_sst.npy')
dates = [dt.date.fromisoformat(s) for s in datestrs]
n_base_win = sum(1 for d in dates if d <= dt.date(2021,6,1))  # placeholder, recompute properly
# recompute properly:
n_base_win = sum(1 for d in dates if d <= dt.date(2003,1,5))
tgt_dates = dates[n_base_win:]
thr_s3 = np.load('/work/thr_s.npy')
sea = np.load('/work/sea_mask.npy')
sst_t = arr32[n_base_win:].astype(np.float64)

def mdoy(d):
    if d.month <= 2: return (d - dt.date(d.year,1,1)).days + 1
    leap = (d.year%4==0 and (d.year%100!=0 or d.year%400==0))
    return (d - dt.date(d.year,1,1)).days + 1 + (0 if leap else 1)

# day-of-year for each target day
doys = np.array([mdoy(d) for d in tgt_dates])   # (92,)
print('doy range:', doys.min(), doys.max())

# threshold for each target day per cell: (92,60,60)
thr_t = thr_s3[doys-1]     # indexing with doy-1
# hot mask
hot = np.zeros_like(sst_t, dtype=bool)
for i in range(len(tgt_dates)):
    hot[i] = sst_t[i] >= thr_t[i]
print('hot cell-days:', int(hot.sum()), 'of', hot.size)
# land cells: sst NaN >= thr is False, so land is not hot. Force land False anyway.
hot &= sea[None,:,:]

def find_runs_per_cell(hot, sea):
    """Per-cell: runs of >=5 consecutive hot days, then join gaps of 1-2 days.
    Returns boolean mask (time, lat, lon) of cells inside a joined per-cell MHW."""
    nt, nlat, nlon = hot.shape
    mhw = np.zeros_like(hot, dtype=bool)
    for a in range(nlat):
        for b in range(nlon):
            if not sea[a, b]:
                continue
            h = hot[:, a, b]
            # find runs of consecutive True
            idx = np.flatnonzero(h)
            if idx.size == 0: continue
            # split into runs
            breaks = np.where(np.diff(idx) > 1)[0]
            starts = np.concatenate(([0], breaks+1))
            ends = np.concatenate((breaks, [idx.size-1]))
            runs = []  # (start_idx, end_idx) in time
            for s, e in zip(starts, ends):
                s_idx, e_idx = idx[s], idx[e]
                if e_idx - s_idx + 1 >= 5:
                    runs.append([s_idx, e_idx])
            # join runs separated by gaps of 1 or 2 days
            if not runs: continue
            joined = [runs[0]]
            for r in runs[1:]:
                gap = r[0] - joined[-1][1] - 1
                if gap <= 2:
                    joined[-1][1] = r[1]
                else:
                    joined.append(r)
            for s, e in joined:
                mhw[s:e+1, a, b] = True
    return mhw

t0 = time.time()
import time
t0 = time.time()
mhw_mask = find_runs_per_cell(hot, sea)
print('mhw detection done in', round(time.time()-t0,2), 's')
print('MHW cell-days:', int(mhw_mask.sum()))
print('cells with any MHW day:', int(mhw_mask.any(axis=0).sum()))
# distribution of per-cell MHW lengths
np.save('/work/mhw_mask.npy', mhw_mask)
np.save('/work/hot.npy', hot)
