import numpy as np, pickle

with open("/tmp/sst_data.pkl","rb") as f: D = pickle.load(f)
with open("/tmp/thr2.pkl","rb") as f: T = pickle.load(f)

sst_target = D["sst_target"]
cell_idx = T["cell_idx"]
thr_s = T["thr_s"]
time_target = D["time_target"]
nc = len(cell_idx)

CUM = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
doy_t = np.array([CUM[dt.month-1] + dt.day for dt in time_target])
assert (doy_t == np.arange(153, 245)).all()

sst_c = sst_target.reshape(92, 3600)[:, cell_idx]   # (92, nc)
hot = sst_c >= thr_s[doy_t, :]
print("hot fraction:", hot.mean())
print("cells ever hot:", int(hot.any(axis=0).sum()), "of", nc)
counts = hot.sum(axis=1)
print("days with any hot:", int((counts>0).sum()))
print("daily counts (1-31):", counts[:31].tolist())
print("daily counts (32-60):", counts[31:60].tolist())
print("daily counts (61-92):", counts[60:].tolist())

def runs_of(mask):
    out, n, i = [], len(mask), 0
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j+1]: j += 1
            out.append((i, j)); i = j + 1
        else:
            i += 1
    return out

mhw_mask = np.zeros((92, nc), dtype=bool)
hist = {}
n_merged = 0
for c in range(nc):
    r = [r for r in runs_of(hot[:, c]) if r[1] - r[0] + 1 >= 5]
    merged = []
    for s, e in r:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    if len(merged) < len(r): n_merged += 1
    for s, e in merged:
        mhw_mask[s:e+1, c] = True
    hist[len(merged)] = hist.get(len(merged), 0) + 1

print("cells by #MHWs:", dict(sorted(hist.items())))
print("cells where merge happened:", n_merged)

active = mhw_mask.any(axis=1)
print("active days:", int(active.sum()), "of 92; 1-based:", [i+1 for i in range(92) if active[i]])
aruns = runs_of(active)
events = [(time_target[s].strftime("%Y-%m-%d"), time_target[e].strftime("%Y-%m-%d")) for s, e in aruns]
for s, e in aruns:
    print("event:", time_target[s].strftime("%Y-%m-%d"), "->", time_target[e].strftime("%Y-%m-%d"), "len", e-s+1)

with open("/tmp/mhw2_state.pkl","wb") as f:
    pickle.dump({"mhw_mask": mhw_mask, "events": events, "active": active, "hot": hot,
                 "cell_idx": cell_idx}, f)
print("saved /tmp/mhw2_state.pkl")
