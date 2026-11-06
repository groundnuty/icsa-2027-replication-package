import numpy as np, pickle, time
from datetime import date, timedelta

meta = pickle.load(open("/tmp/target.pkl","rb"))
T = meta["T"]                      # (92, 60, 60)
sea = meta["sea"]
tc = pickle.load(open("/tmp/thrclim.pkl","rb"))
thr_s = tc["thr_s"]                # (366, 3600)

leap_cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(d): return leap_cum[d.month-1] + d.day

d0 = date(2017,6,1); d1 = date(2017,8,31)
dates = []
cur = d0
while cur <= d1:
    dates.append(cur); cur += timedelta(days=1)
doys = np.array([doy(d) for d in dates]) - 1   # 0-based
assert len(dates) == 92
print("target doys:", doys.min()+1, doys.max()+1)

Tf = T.reshape(92, 3600)
sea_flat = sea.reshape(3600)
thr_t = thr_s[doys]                     # (92, 3600)
hot = Tf >= thr_t                        # (92, 3600); NaN -> False
print("hot fraction (sea cells):", float(hot[:, sea_flat].mean()),
      "min/max per-cell hot days:", int(hot[:,sea_flat].sum(0).min()), int(hot[:,sea_flat].sum(0).max()))

def cell_mhw(h):
    # h: (nt,) bool -> merged MHW mask (nt,)
    m = np.zeros_like(h)
    if not h.any():
        return m
    idx = np.flatnonzero(h)
    # split into runs
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate([[idx[0]], idx[breaks+1]])
    ends   = np.concatenate([idx[breaks], [idx[-1]]])
    runs = [(s,e) for s,e in zip(starts, ends) if e-s+1 >= 5]
    # one-pass merge of gaps <= 2
    merged = []
    for s,e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s,e])
    for s,e in merged:
        m[s:e+1] = True
    return m

t0=time.time()
M = np.zeros((92, 3600), dtype=bool)
for c in np.flatnonzero(sea_flat):
    M[:, c] = cell_mhw(hot[:, c])
print("per-cell MHW done in", round(time.time()-t0,1), "s")
print("cells with >=1 MHW:", int(M.any(axis=0)[sea_flat].sum()))

# regional activity and events
active = M[:, sea_flat].any(axis=1)
events = []
i = 0
while i < 92:
    if active[i]:
        j = i
        while j+1 < 92 and active[j+1]:
            j += 1
        events.append((dates[i], dates[j]))
        i = j+1
    else:
        i += 1
print("active days:", int(active.sum()), "/", 92)
print("events:")
for e in events:
    print("  ", e[0].isoformat(), "->", e[1].isoformat(), f"({ (e[1]-e[0]).days+1 } days)")
pickle.dump({"M":M, "active":active, "events":events, "dates":[d.isoformat() for d in dates]}, open("/tmp/mhwres.pkl","wb"))
print("saved /tmp/mhwres.pkl")
