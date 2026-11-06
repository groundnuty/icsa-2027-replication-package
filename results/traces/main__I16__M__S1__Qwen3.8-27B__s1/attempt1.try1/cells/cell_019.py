import numpy as np, datetime as dt, json
from datetime import date
Xall = np.load("/tmp/Xall.npy")
X_t = Xall[4028:].reshape(92, 3600)
thr_s = np.load("/tmp/thr_s.npy")
ocean = np.load("/tmp/ocean.npy")

def doy(d): return date(2000,d.month,d.day).toordinal()-date(2000,1,1).toordinal()+1
tdays = [date(2008,6,1)+dt.timedelta(i) for i in range(92)]
tdoy = np.array([doy(d) for d in tdays])
print("target DOY:", tdoy.min(), tdoy.max())

hot = np.zeros((92, 3600), bool)
T = thr_s[tdoy-1, :]
hot[:, ocean] = X_t[:, ocean] >= T[:, ocean]
print("hot frac:", round(float(hot.mean()),4))

mhw = np.zeros((92, 3600), bool)
ncells_with_mhw = 0
for c in np.nonzero(ocean)[0]:
    h = hot[:, c]
    if not h.any(): continue
    d = np.diff(np.concatenate(([0], h.view(np.int8), [0])))
    starts = np.nonzero(d==1)[0]
    ends   = np.nonzero(d==-1)[0] - 1
    keep = (ends - starts + 1) >= 5
    starts, ends = starts[keep], ends[keep]
    if len(starts) == 0: continue
    ms, me = [starts[0]], [ends[0]]
    for s, e in zip(starts[1:], ends[1:]):
        if s - me[-1] - 1 <= 2:
            me[-1] = e
        else:
            ms.append(s); me.append(e)
    m = np.zeros(92, bool)
    for s, e in zip(ms, me):
        m[s:e+1] = True
    mhw[:, c] = m
    ncells_with_mhw += 1
print("cells with >=1 MHW:", ncells_with_mhw, "| mhw days total:", int(mhw.sum()))

active = mhw.any(axis=1)
runs = []
inrun = False
for t in range(92):
    if active[t] and not inrun:
        onset = t; inrun = True
    elif not active[t] and inrun:
        runs.append((onset, t-1)); inrun = False
if inrun: runs.append((onset, 91))
events = [{"onset": tdays[a].isoformat(), "end": tdays[b].isoformat()} for a,b in runs]
print("events:", events)
np.save("/tmp/mhw.npy", mhw)
json.dump({"events": events, "runs": runs, "active_frac": float(active.mean())}, open("/tmp/events.json","w"))
print("done")
