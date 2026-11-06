import numpy as np, json, datetime as dt
OUT="/tmp/mhw"
ext = np.load(f"{OUT}/ext.npy").reshape(4028, 3600)
dates = json.load(open(f"{OUT}/dates.json"))
ext_dates = [dt.date.fromisoformat(s) for s in dates["ext_dates"]]
ext_idx = {d:i for i,d in enumerate(ext_dates)}
MS = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
doy = lambda d: MS[d.month-1]+d.day
base_dates = ext_dates[5:5+4018]
D_base = np.array([doy(b) for b in base_dates])
G = np.arange(4018)[:,None] + np.arange(11)[None,:]

c = 12; d = 153
rows = np.flatnonzero(D_base == d)
mask = np.zeros(4028, bool)
mask[G[rows].ravel()] = True
vset = set(np.flatnonzero(mask).tolist())

nset = set()
for b in base_dates:
    if doy(b) != d: continue
    for k in range(-5,6):
        t = b + dt.timedelta(days=k)
        nset.add(ext_idx[t])
print("vec size", len(vset), "naive size", len(nset))
print("only in vec:", sorted(vset - nset))
print("only in naive:", sorted(nset - vset))
# compare values
va = np.sort(ext[np.array(sorted(vset)), c]); va = va[np.isfinite(va)]
vn = np.sort(ext[np.array(sorted(nset)), c]); vn = vn[np.isfinite(vn)]
print("nvals vec", len(va), "naive", len(vn))
print("allclose:", np.allclose(va, vn))
