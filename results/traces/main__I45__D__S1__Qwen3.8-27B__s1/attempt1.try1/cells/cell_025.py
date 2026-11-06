import numpy as np, datetime as dt, json
thr = np.load('/work/thr.npy'); sea = np.load('/work/sea.npy')
target_arr = np.load('/work/target_arr.npy')
doy_target = np.load('/work/doy_target.npy')
Tt, N = target_arr.shape
dates = [dt.date(2009,6,1)+dt.timedelta(days=i) for i in range(Tt)]

hot = (target_arr.T >= thr[:, doy_target]) & np.isfinite(target_arr.T) & sea[:, None]

# independent verification of run detection for cell 164
h164 = hot[164]
d164 = np.diff(np.r_[False, h164, False])
print("cell164 starts:", np.where(d164==1)[0], "ends:", np.where(d164==-1)[0]-1)

mhw = np.zeros((N, Tt), dtype=np.uint8)
n_merged = 0
for c in range(N):
    if not sea[c]:
        continue
    h = hot[c]
    d = np.diff(np.r_[False, h, False])
    starts = np.where(d == 1)[0]
    ends   = np.where(d == -1)[0] - 1
    keep = (ends - starts + 1) >= 5
    starts, ends = starts[keep], ends[keep]
    if len(starts) == 0:
        continue
    gs = [int(starts[0])]; ge = [int(ends[0])]
    for s, e in zip(starts[1:], ends[1:]):
        if int(s) - ge[-1] - 1 <= 2:
            ge[-1] = int(e)
        else:
            gs.append(int(s)); ge.append(int(e))
    if len(gs) > 1:
        n_merged += 1
    for s, e in zip(gs, ge):
        mhw[c, s:e+1] = 1

print("cells with >=1 MHW:", int((mhw.sum(axis=1)>0).sum()), "cells with merged events:", n_merged)
print("total cell-days in MHW:", int(mhw.sum()))
# re-verify cell 164
print("cell164 mhw sum now:", int(mhw[164].sum()))

active = mhw.any(axis=0)
events = []
in_ev = False
for t in range(Tt):
    if active[t] and not in_ev:
        onset = dates[t]; in_ev = True
    if (not active[t] or t == Tt-1) and in_ev:
        endd = dates[t] if active[t] else dates[t-1]
        events.append((onset, endd)); in_ev = False
print("regional events:")
for e in events:
    print("  ", e[0].isoformat(), "->", e[1].isoformat(), " len", (e[1]-e[0]).days+1)
np.save('/work/mhw.npy', mhw)
json.dump([ [a.isoformat(), b.isoformat()] for a,b in events ], open('/work/events.json','w'))
ac = mhw.sum(axis=0)
print("active cells per day (nonzero only):")
for t in range(Tt):
    if ac[t]: print(dates[t].isoformat(), int(ac[t]))
