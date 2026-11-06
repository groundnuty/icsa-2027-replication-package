import numpy as np, pandas as pd

z = np.load('/work/clim_thr.npz')
thr_s, clim_s, sea, tgt_doy = z['thr_s'], z['clim_s'], z['sea'], z['tgt_doy']
sst_tgt = np.load('/work/sst_tgt.npy').astype(np.float64)  # (92,60,60)
tgt_dates = pd.read_pickle('/work/tgt_dates.pkl')
nd = len(tgt_dates)

# sanity: clim/thr finite on sea cells
print("thr_s finite on sea cells for all doy:", bool(np.isfinite(thr_s[1:][:, sea]).all()))
print("clim_s finite on sea cells for all doy:", bool(np.isfinite(clim_s[1:][:, sea]).all()))
sm = lambda a: float(np.nanmean(a[:, sea]))
print("clim_s sea-mean doy153/182/244: %.2f %.2f %.2f K" % (sm(clim_s[153:154]), sm(clim_s[182:183]), sm(clim_s[244:245])))
print("thr_s  sea-mean doy153/182/244: %.2f %.2f %.2f K" % (sm(thr_s[153:154]), sm(thr_s[182:183]), sm(thr_s[244:245])))

# step 3a: hot days (SST >= smoothed threshold for that day-of-year)
thr_days = thr_s[tgt_doy]                # (92,60,60)
hot = sst_tgt >= thr_days                # NaN>=x -> False on land
hot &= sea[None,:,:]
print("hot days fraction (sea cells):", float(hot[:, sea].mean()))

def find_runs(flags_1d, minlen):
    """list of (start,end) inclusive of runs of True with length>=minlen"""
    runs = []
    n = len(flags_1d); i = 0
    while i < n:
        if flags_1d[i]:
            j = i
            while j+1 < n and flags_1d[j+1]: j += 1
            if j-i+1 >= minlen: runs.append([i,j])
            i = j+1
        else:
            i += 1
    return runs

def join_runs(runs, maxgap):
    """merge runs separated by <=maxgap non-hot days (gap days belong to event)"""
    if not runs: return []
    merged = [runs[0][:]]
    for s,e in runs[1:]:
        if s - merged[-1][1] - 1 <= maxgap and s - merged[-1][1] - 1 >= 1:
            merged[-1][1] = e
        else:
            merged.append([s,e])
    return merged

per_cell = np.zeros((nd,60,60), dtype=bool)
n_mhw_cells = 0
for ci in range(60):
    for cj in range(60):
        if not sea[ci,cj]: continue
        runs = find_runs(hot[:,ci,cj], 5)
        if not runs: continue
        evs = join_runs(runs, 2)
        n_mhw_cells += len(evs)
        for s,e in evs:
            per_cell[s:e+1, ci, cj] = True
print("total per-cell MHW events (over all sea cells):", n_mhw_cells)

# step 4: active days & regional events
active = per_cell.any(axis=(1,2))
print("active days:", int(active.sum()), "of", nd)
regional = join_runs(find_runs(active, 1), 0)   # maximal runs of consecutive active days
print("regional events:", len(regional))
for s,e in regional:
    print("  event:", tgt_dates[s].date(), "->", tgt_dates[e].date(), f"({e-s+1} days)")

np.save('/work/per_cell.npy', per_cell)
np.save('/work/active.npy', active)
import json
with open('/work/regional.json','w') as fh:
    json.dump([[int(s),int(e)] for s,e in regional], fh)
print("saved")
