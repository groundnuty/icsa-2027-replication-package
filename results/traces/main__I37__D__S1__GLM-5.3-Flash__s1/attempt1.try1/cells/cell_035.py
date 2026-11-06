import numpy as np, datetime as dt, time

sst = np.load('/work/sst_cube.npy')
times = np.load('/work/times.npy').astype('datetime64[D]')
sea = np.load('/work/sea_mask.npy')
thr_s = np.load('/work/thr_smoothed.npy')   # (366, C)
i0, i1 = 4028, 4119

CUM = [31,29,31,30,31,30,31,31,30,31,30,31]
def dayofyear(d):
    return sum(CUM[:d.month-1]) + d.day

dates_t = [dt.date(2012,6,1)+dt.timedelta(days=k) for k in range(92)]
assert all(times[i0+k] == np.datetime64(dates_t[k]) for k in range(92))

sea_flat_idx = np.where(sea.ravel())[0]
sst_t = sst[i0:i1+1].reshape(92, -1)[:, sea_flat_idx]     # (92, C)
doys_t = np.array([dayofyear(d) for d in dates_t])
print("target doys:", doys_t[0], doys_t[-1])

hot = sst_t >= thr_s[doys_t-1, :]     # (92, C) >= comparison
print("hot days fraction:", hot.mean().round(4))

C = sst_t.shape[1]
# runs of consecutive True >= 5; gaps of <= 2 False joined
runs = np.zeros_like(hot, dtype=bool)
cc = int(hot.sum())
for c in range(C):
    h = hot[:, c]
    # find runs of True
    d = np.diff(np.concatenate(([0], h.view(np.int8), [0])))
    starts = np.where(d == 1)[0]
    ends = np.where(d == -1)[0]  # exclusive
    hot_runs = [(s, e) for s, e in zip(starts, ends) if e - s >= 5]
    if not hot_runs:
        continue
    # join gaps of 1-2 days between consecutive hot runs
    merged = [list(hot_runs[0])]
    for s, e in hot_runs[1:]:
        if s - merged[-1][1] <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    for s, e in merged:
        runs[s:e, c] = True

print("MHW cell-days before/after join:", hot.sum(), runs.sum())
np.save('/work/mhw_runs.npy', runs)

# events
active = runs.any(axis=1)
idx = np.where(active)[0]
events = []
if len(idx):
    splits = np.where(np.diff(idx) > 1)[0]
    groups = np.split(idx, splits+1)
    for g in groups:
        events.append((int(g[0]), int(g[-1])))
print("active days:", int(active.sum()), "of 92")
for (s, e) in events:
    print("event:", dates_t[s], "->", dates_t[e], f"({e-s+1} days)")
np.save('/work/active.npy', active)
