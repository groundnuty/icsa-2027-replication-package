import numpy as np, datetime as dt, pickle

targ_sst = np.load('/tmp/targ_sst.npy')
thr = np.load('/tmp/thr.npy'); clim = np.load('/tmp/clim.npy')
hot = np.load('/tmp/hot.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')
with open('/tmp/meta.pkl','rb') as f: meta = pickle.load(f)
targ_dates = [dt.date.fromisoformat(s) for s in meta['targ_dates']]
targ_str = [d.isoformat() for d in targ_dates]
sea = np.isfinite(targ_sst.astype(np.float64)).all(axis=0)

# ---- independent state-machine detection per cell ----
def detect_independent(hotcol):
    # candidates: runs >=5
    runs = []
    k = 0; n = len(hotcol)
    while k < n:
        if hotcol[k]:
            s = k
            while k < n and hotcol[k]: k += 1
            if k - s >= 5: runs.append((s, k-1))
        else:
            k += 1
    if not runs: return np.zeros(n, bool)
    # join gaps of 1-2 between consecutive kept runs
    joined = [list(runs[0])]
    for s,e in runs[1:]:
        if s - joined[-1][1] - 1 in (1,2): joined[-1][1] = e
        else: joined.append([s,e])
    out = np.zeros(n, bool)
    for s,e in joined: out[s:e+1] = True
    return out

mhw2 = np.zeros_like(mhw_mask, dtype=bool)
for i in range(60):
    for j in range(60):
        if sea[i,j]:
            mhw2[:, i, j] = detect_independent(hot[:, i, j])
print("mask agrees with independent detector:", np.array_equal(mhw_mask.astype(bool), mhw2))
print("mask cell-days:", int(mhw_mask.sum()), " independent:", int(mhw2.sum()))

# ---- recompute hot / active / events independently ----
def doy366(d):
    if d.month==2 and d.day==29: return 60
    if d.month<=2: return (d-dt.date(d.year,1,1)).days+1
    return 61+(d-dt.date(d.year,3,1)).days
targ_doy = np.array([doy366(d) for d in targ_dates])
hot2 = targ_sst.astype(np.float64) >= thr[targ_doy-1]
print("hot agrees:", np.array_equal(hot, hot2))
active = mhw2.any(axis=(1,2))
evs = []
k = 0
while k < 92:
    if active[k]:
        s = k
        while k < 92 and active[k]: k += 1
        evs.append((targ_str[s], targ_str[k-1]))
    else: k += 1
print("events (independent):", evs)
with open('/tmp/events.pkl','rb') as f: events = pickle.load(f)
print("events (pipeline):", events, " agree:", evs == events)

# ---- detail: which cells are in MHW each active day ----
days_active = np.flatnonzero(active)
for t in days_active:
    nc = int(mhw2[t].sum())
    ii, jj = np.where(mhw2[t])
    print(f"{targ_str[t]}: cells in MHW={nc}, lat {lat_vals[t][0] if False else ''}"
          f"lat {54.46+0.02*ii.min():.2f}-{54.46+0.02*ii.max():.2f}, lon {16.06+0.02*jj.min():.2f}-{16.06+0.02*jj.max():.2f}")

# per-cell MHW count map
percell_count = mhw2.sum(axis=0)
print("cells with >=1 MHW day:", int((percell_count>0).sum()), " max days in MHW per cell:", int(percell_count.max()))
