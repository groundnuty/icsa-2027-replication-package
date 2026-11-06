import numpy as np, datetime
hot = np.load('/work/hot.npy'); mask = np.load('/work/mask.npy'); sea = np.load('/work/sea.npy')
T, C = hot.shape

# ---- independent implementation: runs -> dilate by 2 -> connected components -> spans ----
prev = np.empty((T, C), bool); prev[0] = False; prev[1:] = hot[:-1]
nxt  = np.empty((T, C), bool); nxt[-1] = False; nxt[:-1] = hot[1:]
starts = (hot & ~prev)
ends   = (hot & ~nxt)
# run length per run start: use forward fill of run starts
start_idx = np.where(starts, np.broadcast_to(np.arange(T)[:, None], (T, C)), 0)
run_id_start = np.maximum.accumulate(start_idx, axis=0)  # value of last start at/before t
runlen = np.broadcast_to(np.arange(T)[:, None], (T, C)) - run_id_start + 1
is_run_start_ok = starts & (runlen >= 5)
# a day belongs to a >=5 run iff the run containing it has length >=5:
# length of run containing day t = (end of that run) - (start of that run) + 1
end_idx = np.where(ends, np.broadcast_to(np.arange(T)[:, None], (T, C)), 0)
run_id_end = np.minimum.accumulate(end_idx[::-1, :], axis=0)[::-1]  # next end at/after t
runlen2 = run_id_end - run_id_start + 1
R = is_run_start_ok & runlen2   # (T, C): days inside a >=5-day run  [runlen2 gives the length of the containing run; need >=5]
R = (runlen2 >= 5) & hot
# dilate by radius 2
Rd = np.zeros_like(R)
for k in range(-2, 3):
    sh = np.roll(R, k, axis=0)
    if k < 0: sh[:k] = False
    if k > 0: sh[T-k:] = False
    Rd |= sh
# connected components on Rd (axis 0)
lab = np.zeros_like(Rd, dtype=np.int64)
cur = 0
for c in range(C):
    r = Rd[:, c]
    if not r.any(): continue
    b = np.flatnonzero(r & ~np.r_[True, r[:-1]])
    for j, s in enumerate(b):
        e = (b[j+1]-1) if j+1 < len(b) else T-1
        cur += 1
        lab[s:e+1, c] = cur
# final span per component: from first R-day to last R-day within the component
mask2 = np.zeros_like(R)
for c in range(C):
    for labv in np.unique(lab[:, c]):
        if labv == 0: continue
        rr = np.flatnonzero(R[:, c] & (lab[:, c] == labv))
        mask2[rr.min():rr.max()+1, c] = True

print("masks identical:", np.array_equal(mask, mask2))
if not np.array_equal(mask, mask2):
    d = np.flatnonzero((mask != mask2).any(axis=1))
    print("differing days:", d, "cells:", int((mask != mask2).sum()))

# eye check: pick cells with MHWs in event 1 and event 2
tgt_dates = [datetime.date(2009,6,1) + datetime.timedelta(days=k) for k in range(92)]
cells_ev1 = np.flatnonzero(mask[25:36].any(axis=0) & sea)
cells_ev2 = np.flatnonzero(mask[65:70].any(axis=0) & sea)
print("cells in ev1 span:", cells_ev1.size, "ev2 span:", cells_ev2.size)
for c in [cells_ev1[0], cells_ev2[0], cells_ev1[len(cells_ev1)//2]]:
    seq = ''.join('#' if h else ('.' if k<46 else ' ') for k,(h) in enumerate(hot[:,c]))
    seq = ''.join('#' if hot[k,c] else ('.' if 20<=k<=40 else 'o' if 60<=k<=74 else ' ') for k in range(T))
    print(f"cell {c}: hot seq [Jun1..Aug31]:")
    print("  ", seq)
    mm = ''.join('X' if mask[k,c] else ('.' if 20<=k<=40 else 'o' if 60<=k<=74 else ' ') for k in range(T))
    print("   MHW mask:              ", mm)
print("   day index 20=Jun21 35=Jul6 45=Jul16 60=Aug6 69=Aug15 74=Aug20")
