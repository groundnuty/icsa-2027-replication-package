
import numpy as np, pickle, datetime as dt, warnings
warnings.filterwarnings("ignore")
dates = pickle.load(open("/work/dates.pkl","rb"))
tgt = dates["target"]; nT = len(tgt); NC = 3600
St = np.empty((nT, NC), np.float64)
for i, s in enumerate(tgt):
    St[i] = np.load(f"/work/reg/{s}.npy").ravel()
sea = np.isfinite(St).all(axis=0)
thr_s = np.load("/work/thr_s.npy")
percell = np.load("/work/percell.npy")
doyT = np.load("/work/doyT.npy")

# independent hot recompute
hot2 = np.zeros((nT, NC), bool)
hot2[:, sea] = St[:, sea] >= thr_s[doyT-1][:, sea]
print("hot matches saved percell-input (via recompute):", bool((hot2 == (St >= thr_s[doyT-1]) & sea[:,None])).all()))

# independent MHW: union-find over long runs
def mwf_unionfind(m):
    n = len(m); out = np.zeros(n, bool)
    if not m.any(): return out
    # runs
    runs = []
    i = 0
    while i < n:
        if m[i]:
            j = i
            while j+1 < n and m[j+1]: j += 1
            if j - i + 1 >= 5: runs.append([i, j])
            i = j+1
        else:
            i += 1
    R = len(runs)
    parent = list(range(R))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for a in range(R-1):
        gap = runs[a+1][0] - runs[a][1] - 1
        if gap <= 2:
            parent[find(a)] = find(a+1)
    comp = {}
    for r in range(R):
        comp.setdefault(find(r), []).append(r)
    for rs in comp.values():
        st = min(rs_[0] for rs_ in [runs[r] for r in rs])
        en = max(rs_[1] for rs_ in [runs[r] for r in rs])
        out[st:en+1] = True
    return out

n_checked = 0; mism = 0
for c in np.where(sea)[0]:
    if not (mwf_unionfind(hot2[:, c]) == percell[:, c]).all():
        mism += 1
    n_checked += 1
print("cells checked:", n_checked, "mismatches:", mism)

# regional events independent recompute
active = percell.any(axis=1)
ev = []
i = 0
while i < nT:
    if active[i]:
        j = i
        while j+1 < nT and active[j+1]: j += 1
        ev.append((tgt[i], tgt[j]))
        i = j+1
    else: i += 1
saved = pickle.load(open("/work/events.pkl","rb"))
print("events recomputed:", ev)
print("events match saved:", ev == saved["events"])
# per-day active counts around event edges
print("active flags around start:", [(tgt[k], bool(active[k])) for k in range(0,8)])
print("active flags around end:", [(tgt[k], bool(active[k])) for k in range(nT-8, nT)])
print("num events:", len(ev), "total active days:", int(active.sum()))
