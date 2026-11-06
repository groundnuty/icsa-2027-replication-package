import numpy as np, datetime as dt, json, os

hot = np.load('work/hot.npy')          # (92, 60, 60) bool
T = np.load('work/T.npy').astype(np.float64)
thr_s = np.load('work/thr_s.npy')
clim_s = np.load('work/clim_s.npy')
tdates = [dt.date(2021,6,1)+dt.timedelta(days=i) for i in range(92)]

def leap(y): return y%4==0 and (y%100!=0 or y%400==0)
def doy_of(d):
    n = (d - dt.date(d.year,1,1)).days + 1
    if d.month >= 3 and not leap(d.year): n += 1
    return n
tdoy = np.array([doy_of(d) for d in tdates])

def per_cell_mhw(h):
    mhw = np.zeros(len(h), dtype=bool)
    idx = np.flatnonzero(h)
    if len(idx) == 0:
        return mhw
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate([[idx[0]], idx[breaks + 1]])
    ends = np.concatenate([idx[breaks], [idx[-1]]])
    cand = [(s, e) for s, e in zip(starts, ends) if e - s + 1 >= 5]
    if not cand:
        return mhw
    merged = [list(cand[0])]
    for s, e in cand[1:]:
        if s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    for s, e in merged:
        mhw[s:e+1] = True
    return mhw

nt, nlat, nlon = hot.shape
mhw_mask = np.zeros_like(hot)
per_cell_events = []   # for diagnostics: (cell, start_idx, end_idx)
for i in range(nlat):
    for j in range(nlon):
        m = per_cell_mhw(hot[:, i, j])
        mhw_mask[:, i, j] = m
        idx = np.flatnonzero(m)
        if len(idx):
            brk = np.flatnonzero(np.diff(idx) > 1)
            st = np.concatenate([[idx[0]], idx[brk+1]])
            en = np.concatenate([idx[brk], [idx[-1]]])
            for s, e in zip(st, en):
                per_cell_events.append((int(s), int(e)))

# hot days inside per-cell MHWs vs all hot days (gap days are included in mhw but may be non-hot)
print("per-cell MHW cell-day count:", mhw_mask.sum(), "| cells with >=1 MHW:", (mhw_mask.any(axis=0)).sum(), "of", fin_all.sum() if (fin_all:=np.isfinite(T).all(axis=0)).all() else (np.isfinite(T).all(axis=0)).sum())
print("n per-cell MHW events:", len(per_cell_events))
lens = [e-s+1 for s,e in per_cell_events]
print("per-cell event lengths: min", min(lens), "max", max(lens), "mean %.1f" % np.mean(lens))

# regional: active = any cell inside per-cell MHW
active = mhw_mask.any(axis=(1,2))     # (92,)
print("active days:", active.sum(), "of", nt)
# events: maximal runs of consecutive active days
idx = np.flatnonzero(active)
events = []
if len(idx):
    brk = np.flatnonzero(np.diff(idx) > 1)
    st = np.concatenate([[idx[0]], idx[brk+1]])
    en = np.concatenate([idx[brk], [idx[-1]]])
    events = [(int(s), int(e)) for s, e in zip(st, en)]
print("n regional events:", len(events))
for s, e in events:
    print("  event:", tdates[s].isoformat(), "->", tdates[e].isoformat(), f"({e-s+1} days)")

np.save('work/mhw_mask.npy', mhw_mask)
with open('work/events.json','w') as f_:
    json.dump(events, f_)
print("saved mhw_mask and events.")
