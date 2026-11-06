import numpy as np, pickle
from datetime import date

thr = np.load('/work/thr_raw.npy'); thr_s = np.load('/work/thr_smooth.npy')
# correct day365 window: 350..365 (16) + 0..14 (15)
manual365 = np.nanmean(np.concatenate([thr[350:366], thr[0:15]], axis=0), axis=0)
print("day365 check (all):", np.allclose(thr_s[365], manual365, equal_nan=True))

# ---- independent MHW re-implementation (interval-merge style) on all cells ----
with open('/work/dates.pkl','rb') as f: dd = pickle.load(f)
tgt_dates = dd['tgt']
nb = len(dd['base'])
SST = np.load('/work/SST_all.npy')
sea = np.load('/work/sea_mask.npy').ravel()
mhw = np.load('/work/mhw.npy')

def mdoy(dt): return (date(2000, dt.month, dt.day) - date(2000,1,1)).days + 1
doys = np.array([mdoy(d) for d in tgt_dates])
tgt = SST[nb:].reshape(len(tgt_dates), 3600)

mhw2 = np.zeros_like(mhw)
for c in range(3600):
    if not sea[c]: continue
    h = tgt[:, c] >= thr_s[doys - 1, c]
    n = len(h)
    # collect maximal hot intervals as (start, end) inclusive
    ivs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j < n and h[j]: j += 1
            if j - i >= 5: ivs.append([i, j-1])
            i = j
        else:
            i += 1
    # merge intervals with gap 1 or 2
    out = []
    for s, e in ivs:
        if out and s <= out[-1][1] + 3:   # gap = s - out[-1][1] - 1 <= 2
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    for s, e in out:
        mhw2[s:e+1, c] = 1
print("independent MHW re-implementation matches:", np.array_equal(mhw, mhw2))

# active & events recompute independently
active = mhw2.any(axis=1)
ev2 = []
i = 0; n = len(active)
while i < n:
    if active[i]:
        j = i
        while j < n and active[j]: j += 1
        ev2.append((tgt_dates[i].isoformat(), tgt_dates[j-1].isoformat()))
        i = j
    else:
        i += 1
print("events:", ev2)
