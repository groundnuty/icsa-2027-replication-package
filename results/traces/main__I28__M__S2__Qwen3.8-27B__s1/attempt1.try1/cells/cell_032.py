import numpy as np, pickle

with open("/tmp/sst_data.pkl","rb") as f: D = pickle.load(f)
with open("/tmp/mhw2_state.pkl","rb") as f: S = pickle.load(f)
with open("/tmp/thr2.pkl","rb") as f: T = pickle.load(f)
time_target = D["time_target"]
cell_idx = S["cell_idx"]; nc = len(cell_idx)
mhw_ref = S["mhw_mask"]; events_ref = S["events"]

CUM = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])

# FIXED independent smoothing: 1-based day D averages days D-15..D+15 (mod 366)
def smooth31(a):
    out = np.empty_like(a)
    for d in range(366):          # 0-based index d
        idx = [(d + k) % 366 for k in range(-15, 16)]
        out[d] = a[idx].mean(axis=0)
    return out
thr2s = smooth31(T["thr"])
print("smoothed thr identical:", bool(np.allclose(thr2s, T["thr_s"], equal_nan=True)))

doy_t = np.array([CUM[dt.month-1] + dt.day for dt in time_target])
sst_c = D["sst_target"].reshape(92, 3600)[:, cell_idx]
hot2 = sst_c >= thr2s[doy_t, :]
print("hot identical:", bool((hot2 == S["hot"]).all()))

def runs2(mask):
    dd = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(dd == 1), np.flatnonzero(dd == -1) - 1))

mhw2 = np.zeros((92, nc), dtype=bool)
for c in range(nc):
    rs = [r for r in runs2(hot2[:, c]) if r[1]-r[0]+1 >= 5]
    changed = True
    while changed:
        changed = False; new = []
        for r in rs:
            if new and r[0] - new[-1][1] - 1 <= 2:
                new[-1] = (new[-1][0], r[1]); changed = True
            else:
                new.append(r)
        rs = new
    for s, e in rs:
        mhw2[s:e+1, c] = True
print("mhw mask identical:", bool((mhw2 == mhw_ref).all()))

active2 = mhw2.any(axis=1)
ar = runs2(active2)
events2 = [(time_target[s].strftime("%Y-%m-%d"), time_target[e].strftime("%Y-%m-%d")) for s, e in ar]
print("events ref:", events_ref)
print("events new:", events2)
print("events identical:", events_ref == events2)

# extra: verify every per-cell MHW span contains a run of >=5 hot days (gap days may extend it)
bad = 0
for c in range(nc):
    if not mhw2[:, c].any(): continue
    for s, e in runs2(mhw2[:, c]):
        seg = S["hot"][s:e+1, c]
        # longest hot run in segment
        mx = 0; cur = 0
        for v in seg:
            cur = cur + 1 if v else 0
            mx = max(mx, cur)
        if mx < 5: bad += 1
print("MHW spans lacking a >=5 hot run:", bad)

# verify gap days inside merged spans are non-hot where not covered by hot runs (structural check of merge)
print("max merged-span length:", max((e-s+1) for c in range(nc) if mhw2[:,c].any() for s,e in runs2(mhw2[:,c])))
