import numpy as np, datetime as dt, json

thr_s = np.load('/tmp/thr_s.npy')   # (367,60,60), index 0 unused
tgt   = np.load('/tmp/tgt_cube.npy')  # (92,60,60) float64, Kelvin
tgt_days = [dt.date(2021,6,1)+dt.timedelta(days=i) for i in range(92)]
def mdoy(d): return (dt.date(2000,d.month,d.day)-dt.date(2000,1,1)).days+1
tdoy = np.array([mdoy(d) for d in tgt_days])
print("target doys:", tdoy[0], "..", tdoy[-1])

sea = np.isfinite(tgt).all(axis=0)
print("sea cells:", int(sea.sum()))

# hot days: SST >= threshold (NaN comparisons -> False naturally)
thr_t = thr_s[tdoy]                      # (92,60,60)
hot = np.greater_equal(tgt, thr_t, where=~np.isnan(tgt), out=np.zeros_like(tgt, dtype=bool))
hot = hot & ~np.isnan(tgt) & ~np.isnan(thr_t)
print("total hot cell-days:", int(hot.sum()), "| hot among sea cells:", int(hot[:, sea].sum()))

nT = 92
mhw = np.zeros((nT, 60, 60), dtype=bool)
stats = {'candidates': 0, 'joined_groups': 0, 'kept5': 0, 'joined_runs': 0, 'gap_days_added': 0}
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        h = hot[:, i, j]
        if not h.any(): continue
        # candidate runs of consecutive hot days
        runs = []
        t = 0
        while t < nT:
            if h[t]:
                s = t
                while t < nT and h[t]: t += 1
                runs.append([s, t-1])
            else:
                t += 1
        stats['candidates'] += len(runs)
        # join runs separated by 1-2 non-hot days
        groups = []
        for r in runs:
            if groups and r[0] - groups[-1][1] - 1 <= 2:
                groups[-1][1] = r[1]
            else:
                groups.append(list(r))
        stats['joined_groups'] += len(groups)
        kept = 0
        for s, e in groups:
            if e - s + 1 >= 5:
                mhw[s:e+1, i, j] = True
                kept += 1
                stats['gap_days_added'] += int((~h[s:e+1]).sum())
        stats['kept5'] += kept
print(stats)
print("total MHW cell-days:", int(mhw.sum()))
# per-day active cells
act_cells = mhw.sum(axis=(1,2))
active = act_cells > 0
print("active days:", int(active.sum()), "of", nT)
for t in range(nT):
    if active[t]:
        print(tgt_days[t], "cells in MHW:", int(act_cells[t]))
