import numpy as np, datetime as dt

mhw_mask = np.load('work/mhw_mask.npy')
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
print("active days identical (mask.any vs per-cell events):", np.array_equal(active1, active2))

idx = np.flatnonzero(active1)
brk = np.flatnonzero(np.diff(idx) > 1)
st = np.concatenate([[idx[0]], idx[brk+1]]); en = np.concatenate([idx[brk], [idx[-1]]])
evs = [(tdates[int(a)].isoformat(), tdates[int(b)].isoformat(), int(b-a+1)) for a, b in zip(st, en)]
print("regional events:", evs)
print("inactive days:", [tdates[int(k)].isoformat() for k in np.where(~active1)[0]])

# 3) verify joined gap days are in mask even if not hot
gap_cells = 0
shown = 0
for i in range(60):
    for j in range(60):
        m = mhw_mask[:, i, j]; h = hot[:, i, j]
        gapdays = m & ~h
        if gapdays.any():
            gap_cells += 1
            if shown < 3:
                k = int(np.flatnonzero(gapdays)[0])
                print(f"cell({i},{j}) gap day {tdates[k].isoformat()}: in MHW, hot? {bool(h[k])}; mask k-2..k+2:", m[max(k-2,0):k+3].astype(int), "hot:", h[max(k-2,0):k+3].astype(int))
                shown += 1
print("cells with gap days inside MHWs:", gap_cells)

# 4) spot-check cell (30,30)
T = np.load('work/T.npy').astype(np.float64)
thr_s = np.load('work/thr_s.npy')
def leap(y): return y%4==0 and (y%100!=0 or y%400==0)
def doy_of(d):
    n = (d - dt.date(d.year,1,1)).days + 1
    if d.month >= 3 and not leap(d.year): n += 1
    return n
i, j = 30, 30
hot_loop = np.array([(np.isfinite(T[k,i,j]) and T[k,i,j] >= thr_s[doy_of(tdates[k])-1, i, j]) for k in range(92)])
print("cell(30,30) hot identical:", np.array_equal(hot_loop, hot[:, i, j]))
m = mhw_mask[:, i, j]
idx = np.flatnonzero(m); brk = np.flatnonzero(np.diff(idx) > 1)
st = np.concatenate([[idx[0]], idx[brk+1]]); en = np.concatenate([idx[brk], [idx[-1]]])
print("cell(30,30) MHW runs:", [(tdates[int(a)].isoformat(), tdates[int(b)].isoformat(), int(b-a+1)) for a, b in zip(st, en)])
idx = np.flatnonzero(hot[:, i, j]); brk = np.flatnonzero(np.diff(idx) > 1)
st = np.concatenate([[idx[0]], idx[brk+1]]); en = np.concatenate([idx[brk], [idx[-1]]])
print("cell(30,30) raw hot runs:", [(tdates[int(a)].isoformat(), tdates[int(b)].isoformat(), int(b-a+1)) for a, b in zip(st, en)])
