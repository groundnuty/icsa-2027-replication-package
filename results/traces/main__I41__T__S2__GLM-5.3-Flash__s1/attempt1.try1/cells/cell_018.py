import numpy as np, datetime as dt

mhw_mask = np.load('work/mhw_mask.npy')   # (92, 60, 60) bool
hot = np.load('work/hot.npy')
tdates = [dt.date(2021,6,1)+dt.timedelta(days=i) for i in range(92)]

# 1) recompute regional events from per-cell events directly
per_cell = []
for i in range(60):
    for j in range(60):
        m = mhw_mask[:, i, j]
        idx = np.flatnonzero(m)
        if len(idx):
            brk = np.flatnonzero(np.diff(idx) > 1)
            st = np.concatenate([[idx[0]], idx[brk+1]]); en = np.concatenate([idx[brk], [idx[-1]]])
            per_cell += [(int(s), int(e))]
active2 = np.zeros(92, dtype=bool)
for s, e in per_cell:
    active2[s:e+1] = True
active1 = mhw_mask.any(axis=(1,2))
print("active days identical (mask vs per-cell events):", np.array_equal(active1, active2))
idx = np.flatnonzero(active1)
brk = np.flatnonzero(np.diff(idx) > 1)
st = np.concatenate([[idx[0]], idx[brk+1]]); en = np.concatenate([idx[brk], [idx[-1]]])
print("regional events:", [(tdates[s].isoformat(), tdates[e].isoformat(), int(e-s+1)) for s, e in zip(st, en)])

# 2) gap between events: which days are inactive?
print("inactive days:", [tdates[k].isoformat() for k in np.where(~active1)[0]])

# 3) verify joined gap days are in mask even if not hot
# find cells where mhw has a day not hot inside an MHW (gap day)
gap_examples = 0
for i in range(60):
    for j in range(60):
        m = mhw_mask[:, i, j]; h = hot[:, i, j]
        gapdays = m & ~h
        if gapdays.any() and gap_examples < 3:
            k = np.flatnonzero(gapdays)[0]
            print(f"cell({i},{j}) gap day {tdates[k].date()}: in MHW but not hot -> neighbours hot:", 
                  bool(h[max(k-1,0)]), bool(h[min(k+1,91)]), "| mask around:", m[max(k-2,0):k+3].astype(int))
            gap_examples += 1
print("cells with gap days inside MHWs:", sum(1 for i in range(60) for j in range(60) if (mhw_mask[:,i,j] & ~hot[:,i,j]).any()))

# 4) spot-check one cell fully: recompute hot from stored T and threshold with a loop
T = np.load('work/T.npy').astype(np.float64)
thr_s = np.load('work/thr_s.npy')
import datetime as dt
def leap(y): return y%4==0 and (y%100!=0 or y%400==0)
def doy_of(d):
    n = (d - dt.date(d.year,1,1)).days + 1
    if d.month >= 3 and not leap(d.year): n += 1
    return n
i, j = 30, 30
hot_loop = np.array([ (np.isfinite(T[k,i,j]) and T[k,i,j] >= thr_s[doy_of(tdates[k])-1, i, j]) for k in range(92) ])
print("cell(30,30) hot identical:", np.array_equal(hot_loop, hot[:, i, j]))
m = mhw_mask[:, i, j]
print("cell(30,30) MHW days:", [(tdates[k].isoformat()) for k in np.flatnonzero(m)][:6], "... total", int(m.sum()))
# runs for this cell
idx = np.flatnonzero(m)
brk = np.flatnonzero(np.diff(idx) > 1)
st = np.concatenate([[idx[0]], idx[brk+1]]); en = np.concatenate([idx[brk], [idx[-1]]])
print("cell(30,30) MHW runs:", [(tdates[s].isoformat(), tdates[e].isoformat(), int(e-s+1)) for s, e in zip(st, en)])
# raw hot runs for this cell (before joining)
idx = np.flatnonzero(hot[:, i, j])
brk = np.flatnonzero(np.diff(idx) > 1)
st = np.concatenate([[idx[0]], idx[brk+1]]); en = np.concatenate([idx[brk], [idx[-1]]])
print("cell(30,30) raw hot runs:", [(tdates[s].isoformat(), tdates[e].isoformat(), int(e-s+1)) for s, e in zip(st, en)])
