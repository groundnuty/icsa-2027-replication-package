import numpy as np, datetime as dt, os

st = np.load("/tmp/st.npy")        # (3600, 92)
sea = np.load("/tmp/sea.npy")      # (3600,)
thr_s = np.load("/tmp/thr_s.npy")  # (366, 3301)
doy = np.load("/tmp/doy.npy")      # (4632,)
j0, j1 = 4540, 4631
doy_t = doy[j0:j1+1]               # (92,)
assert len(np.unique(doy_t)) == 92

T = st[sea]                        # (nsea, 92)
nsea = T.shape[0]
hot = T >= thr_s[doy_t - 1].T      # (nsea, 92)
print("hot fraction:", hot.mean())

in_mhw = np.zeros((nsea, 92), dtype=bool)
for i in range(nsea):
    h = hot[i]
    x = np.concatenate([[0], h.astype(np.int8), [0]])
    diff = np.diff(x)
    starts = np.where(diff == 1)[0] + 1
    ends   = np.where(diff == -1)[0]
    keep = (ends - starts + 1) >= 5
    starts, ends = starts[keep], ends[keep]
    merged = []
    for s, e in zip(starts.tolist(), ends.tolist()):
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    for s, e in merged:
        in_mhw[i, s:e+1] = True

mask = np.zeros((3600, 92), dtype=np.uint8)
mask[sea] = in_mhw
print("days with any MHW cell:", int(in_mhw.any(axis=0).sum()))
active = in_mhw.any(axis=0)
# regional events: maximal runs of active days
events = []
s = None
for t in range(92):
    if active[t] and s is None: s = t
    if (not active[t]) and s is not None:
        events.append((s, t-1)); s = None
if s is not None: events.append((s, 91))
base = dt.date(2004,6,1)
ev = [(str(base + dt.timedelta(days=s)), str(base + dt.timedelta(days=e))) for s,e in events]
print("events:", ev)
print("per-cell MHW spans (count of cells with >=1 MHW):", int(in_mhw.any(axis=1).sum()))
lens = [ (e-s+1) for s,e in zip(*[ [r[0] for r in m] for m in [] ])] if False else None

np.save("/tmp/in_mhw.npy", in_mhw)
np.save("/tmp/active.npy", active)
np.save("/tmp/events.npy", np.array(events, dtype=int))
print("saved detection outputs")
