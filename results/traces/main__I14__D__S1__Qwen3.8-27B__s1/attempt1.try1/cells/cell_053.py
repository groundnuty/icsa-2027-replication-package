import numpy as np
from datetime import date
mask = np.load('/work/data/mask.npy')
tt = np.load('/work/data/tt.npy')
si = np.load('/work/data/sea_idx.npy')
tt_dates = [date.fromisoformat(str(np.datetime64(t))[:10]) for t in tt]

active = mask.any(axis=1)
print("active day -> n cells in MHW:")
for i in range(92):
    if active[i]:
        print("  ", tt_dates[i].isoformat(), int(mask[i].sum()))

# independent event scan (written differently from pipeline)
events = []
run = []
for i in range(92):
    if active[i]:
        run.append(i)
    else:
        if run:
            events.append((run[0], run[-1]))
            run = []
if run:
    events.append((run[0], run[-1]))
print("events (independent scan):", [(tt_dates[a].isoformat(), tt_dates[b].isoformat()) for a, b in events])

# which cells are active on 2015-07-01 (idx 30) and 2015-07-08 (idx 37)?
for i in [30, 37]:
    cells = np.flatnonzero(mask[i])
    print(tt_dates[i], "cells in MHW:", len(cells), cells[:10])
# per-cell MHW intervals for the first 8 cells that have any
si_arr = si
cnt = 0
for c in range(mask.shape[1]):
    if mask[:, c].any():
        ivs = []
        i = 0
        while i < 92:
            if mask[i, c]:
                j = i
                while j < 92 and mask[j, c]: j += 1
                ivs.append((tt_dates[i].isoformat()[5:], tt_dates[j-1].isoformat()[5:]))
                i = j
            else:
                i += 1
        r, cc = si_arr[c]//60, si_arr[c]%60
        print("cell", c, "(row", r, "col", cc, ") MHW:", ivs)
        cnt += 1
        if cnt >= 8: break