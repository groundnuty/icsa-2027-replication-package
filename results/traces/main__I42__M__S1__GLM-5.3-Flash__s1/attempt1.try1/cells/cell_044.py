import numpy as np, h5py
from datetime import date, timedelta

sst_t = np.load("/work/sst_target_corr.npy").astype(np.float64)
thr_s = np.load("/work/thr_smooth_corr.npy")
mhw = np.load("/work/mhw_final_corr.npy")
MD_CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
target_dates = []
d = date(2012,6,1)
while d <= date(2012,8,31):
    target_dates.append(d); d += timedelta(days=1)
doys = np.array([MD_CUM[t.month-1]+t.day for t in target_dates])

# per-cell merged events: how many days each, and gap-joining present?
def runs_of(hs):
    runs = []
    i = 0
    while i < len(hs):
        if hs[i]:
            j = i
            while j < len(hs) and hs[j]:
                j += 1
            runs.append((i, j-1)); i = j
        else:
            i += 1
    return runs

gap_joined = 0
single_runs = 0
for ii, jj in zip(*np.where(mhw.any(axis=0))):
    hs = mhw[:, ii, jj]
    rr = runs_of(hs)
    for a, b in rr:
        if b - a + 1 >= 5:
            single_runs += 1
        else:
            gap_joined += 1
print("per-cell MHW runs >= 5 days (uninterrupted):", single_runs)
print("per-cell MHW runs < 5 days (gap-joined portions):", gap_joined)
# total events structure: 
def merged_events(hs):
    rr = runs_of(hs)
    mhw_runs = [r for r in rr if r[1]-r[0]+1 >= 5]
    merged = []
    for r in mhw_runs:
        if merged and r[0]-merged[-1][1]-1 <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    return merged

multi = 0
for ii, jj in zip(*np.where(mhw.any(axis=0))):
    me = merged_events(mhw[:,ii,jj])
    if len(me) > 1:
        multi += 1
print("cells with >1 merged event:", multi)
for (ii,jj) in list(zip(*np.where(mhw.any(axis=0))))[:6]:
    me = merged_events(mhw[:,ii,jj])
    hs = hot if False else None
    # print raw hot runs and merged events
    rr = runs_of((sst_t[:,ii,jj] >= thr_s[doys-1,ii,jj]) & np.isfinite(sst_t[:,ii,jj]))
    print(f"cell({ii},{jj}): hot runs {rr} -> merged {me}")
