import numpy as np, datetime as dt, time

datestrs = np.load('/work/extract_dates.npy')
arr32 = np.load('/work/extract_sst.npy')
dates = [dt.date.fromisoformat(s) for s in datestrs]
n_base_win = sum(1 for d in dates if d <= dt.date(2003,1,5))
tgt_dates = dates[n_base_win:]
thr_s3 = np.load('/work/thr_s.npy')
sea = np.load('/work/sea_mask.npy')
sst_t = arr32[n_base_win:].astype(np.float64)

def mdoy(d):
    if d.month <= 2: return (d - dt.date(d.year,1,1)).days + 1
    leap = (d.year%4==0 and (d.year%100!=0 or d.year%400==0))
    return (d - dt.date(d.year,1,1)).days + 1 + (0 if leap else 1)

doys = np.array([mdoy(d) for d in tgt_dates])
thr_t = thr_s3[doys-1]
hot = (sst_t >= thr_t) & sea[None,:,:]

def find_runs_per_cell(hot, sea):
    nt, nlat, nlon = hot.shape
    mhw = np.zeros_like(hot, dtype=bool)
    for a in range(nlat):
        for b in range(nlon):
            if not sea[a, b]: continue
            h = hot[:, a, b]
            idx = np.flatnonzero(h)
            if idx.size == 0: continue
            breaks = np.where(np.diff(idx) > 1)[0]
            starts = np.concatenate(([0], breaks+1))
            ends = np.concatenate((breaks, [idx.size-1]))
            runs = []
            for s, e in zip(starts, ends):
                if idx[e] - idx[s] + 1 >= 5:
                    runs.append([idx[s], idx[e]])
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
mhw_mask = find_runs_per_cell(hot, sea)
print('mhw detection done in', round(time.time()-t0,2), 's')
print('MHW cell-days:', int(mhw_mask.sum()), 'cells with any MHW:', int(mhw_mask.any(axis=0).sum()))
np.save('/work/mhw_mask.npy', mhw_mask)
np.save('/work/hot.npy', hot)

# Regional events: active day = at least one cell inside per-cell MHW
active = mhw_mask.any(axis=(1,2))
print('active days:', int(active.sum()), 'of', len(active))
# find maximal runs of consecutive active days
idx = np.flatnonzero(active)
if idx.size:
    breaks = np.where(np.diff(idx) > 1)[0]
    starts = np.concatenate(([0], breaks+1))
    ends = np.concatenate((breaks, [idx.size-1]))
    events = [(int(idx[s]), int(idx[e])) for s, e in zip(starts, ends)]
else:
    events = []
for s, e in events:
    print('event:', tgt_dates[s].isoformat(), '->', tgt_dates[e].isoformat(), f'({e-s+1} days)')
np.save('/work/active.npy', active)
