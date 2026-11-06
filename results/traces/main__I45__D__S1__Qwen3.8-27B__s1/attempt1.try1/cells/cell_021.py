import numpy as np, datetime as dt, json, os
thr = np.load('/work/thr.npy'); sea = np.load('/work/sea.npy')
target_arr = np.load('/work/target_arr.npy')
doy_target = np.load('/work/doy_target.npy')
Tt, N = target_arr.shape
dates = [dt.date(2009,6,1)+dt.timedelta(days=i) for i in range(Tt)]

# hot mask: (N, Tt)
hot = target_arr.T >= thr[:, doy_target]     # NaN comparisons -> False
hot = hot & np.isfinite(target_arr.T)
hot = hot & sea[:, None]

# per-cell runs of >=5 consecutive hot days
runs = np.zeros((N, Tt), dtype=np.int32)   # store run id per cell-day (0 = none)
mhw = np.zeros((N, Tt), dtype=np.uint8)
for c in range(N):
    if not sea[c]:
        continue
    h = hot[c]
    # find hot runs
    starts = np.where(np.r_[h[0], h[1:] & ~h[:-1]] == True)[0]
    ends   = np.where(np.r_[h[1:], h[-1]] == True)[0]
    if len(starts) == 0:
        continue
    starts = starts[(ends - starts + 1) >= 5]
    ends   = ends[(ends - starts + 1) >= 5]
    # join runs separated by 1 or 2 non-hot days
    group_start = [starts[0]]
    group_end   = [ends[0]]
    for s, e in zip(starts[1:], ends[1:]):
        gap = s - group_end[-1] - 1
        if gap <= 2:
            group_end[-1] = e
        else:
            group_start.append(s); group_end.append(e)
    for s, e in zip(group_start, group_end):
        mhw[c, s:e+1] = 1

print("cells with >=1 MHW:", int((mhw.sum(axis=1)>0).sum()))
print("total cell-days in MHW:", int(mhw.sum()))
active = mhw.any(axis=0)
# events
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
