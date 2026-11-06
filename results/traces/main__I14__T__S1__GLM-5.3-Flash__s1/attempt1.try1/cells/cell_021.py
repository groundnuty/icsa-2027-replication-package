import numpy as np, pandas as pd, pickle

with open('/tmp/stepA.pkl','rb') as fh:
    A = pickle.load(fh)
bdates = A['bdates']; arr_sea = A['arr_sea']
m_start = np.array([1,32,61,92,122,153,183,214,245,275,306,336])
bdoy = m_start[bdates.month.values-1] + bdates.day.values - 1

# CORRECT brute-force: date t in pool(d) iff exists k in [-5,5] with remap_doy(t + k days) == d
hit = {}   # d -> set of (y,m,d) of contributing original dates
for k in range(-5, 6):
    sh = bdates + pd.Timedelta(days=k)
    sdoy = m_start[sh.month.values-1] + sh.day.values - 1
    for t, dd in zip(bdates, sdoy):
        if dd == 60: continue
        hit.setdefault(dd, set()).add((t.year, t.month, t.day))

mismatch = 0
for d in range(1, 367):
    if d == 60: continue
    sel = np.isin(bdoy, np.array(sorted({((d + k - 1) % 366) + 1 for k in range(-5, 6)})))
    mine = set(zip(bdates[sel].year, bdates[sel].month, bdates[sel].day))
    if mine != hit.get(d, set()):
        mismatch += 1
        if mismatch <= 5:
            print(f"doy {d}: MISMATCH  mine {len(mine)}  bf {len(hit.get(d,set()))}  "
                  f"mine-only {sorted(mine - hit.get(d,set()))[:3]}  bf-only {sorted(hit.get(d,set()) - mine)[:3]}")
print("pool-membership mismatches over all 365 doys:", mismatch)
sizes = [len(hit[d]) for d in range(1,367) if d != 60]
print("pool date-count: min", min(sizes), "max", max(sizes))

# CORRECT manual Hazen check on a sorted pool
d = 153
sel = np.isin(bdoy, np.array(sorted({((d + k - 1) % 366) + 1 for k in range(-5, 6)})))
pool = np.sort(arr_sea[sel][:, 0])
pool = pool[np.isfinite(pool)]
n = len(pool); pos = 0.9*(n+1); lo = int(np.floor(pos)); frac = pos - lo
q_manual = pool[lo-1] + frac*(pool[lo] - pool[lo-1])
q_np = np.quantile(pool, 0.9, method='hazen')
print(f"doy153 cell0: n={n} pos={pos} manual={q_manual:.6f} numpy={q_np:.6f} match={np.isclose(q_manual, q_np)}")
# one more doy/cell
d = 366
sel = np.isin(bdoy, np.array(sorted({((d + k - 1) % 366) + 1 for k in range(-5, 6)})))
pool = np.sort(arr_sea[sel][:, 777]); pool = pool[np.isfinite(pool)]
n = len(pool); pos = 0.9*(n+1); lo = int(np.floor(pos)); frac = pos-lo
print(f"doy366 cell777: n={n} manual={pool[lo-1]+frac*(pool[lo]-pool[lo-1]):.6f} "
      f"numpy={np.quantile(pool,0.9,method='hazen'):.6f}")
