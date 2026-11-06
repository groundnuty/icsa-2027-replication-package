import pickle, numpy as np, time
from datetime import date, timedelta

with open('/work/dates.pkl','rb') as f: dd = pickle.load(f)
base_dates = dd['base']  # 1991-12-27 .. 2003-01-05
nb = len(base_dates)
SST = np.load('/work/SST_all.npy')[:nb]  # (4028, 60, 60)

# leap-year day of year (Feb has 29): doy(m,d)
doy_table = {}
ref = date(2000,1,1)
for m in range(1,13):
    import calendar
    for d in range(1, calendar.monthrange(2000, m)[1]+1):
        doy_table[(m,d)] = (date(2000,m,d) - ref).days + 1
def mdoy(dt): return doy_table[(dt.month, dt.day)]

b_start, b_end = date(1992,1,1), date(2002,12,31)

# Approach A: for each window date t, contribute to pools of mdoy(b), b in [t-5,t+5] within baseline
t0 = time.time()
pool_idx = {D: [] for D in list(range(1,60)) + list(range(61,367))}
for i, t in enumerate(base_dates):
    lo = t - timedelta(days=5); hi = t + timedelta(days=5)
    if hi < b_start or lo > b_end: continue
    b = lo
    while b <= hi:
        if b_start <= b <= b_end:
            D = mdoy(b)
            if D != 60:
                pool_idx[D].append(i)
        b += timedelta(days=1)
print("pool build time:", time.time()-t0)
sizes = np.array([len(pool_idx[D]) for D in pool_idx], dtype=int)
print("pool size min/max:", sizes.min(), sizes.max())
print("day1 size:", len(pool_idx[1]), "day152 size:", len(pool_idx[152]), "day244 size:", len(pool_idx[244]), "day366 size:", len(pool_idx[366]))
# day 1 check: pools for 1 Jan: window dates t such that some 1 Jan baseline b within 5: t in [Dec 27..Jan 6] of each year -> 
# total = 5 (1991) + 11*11 - ... just print the first/last indices
p1 = pool_idx[1]
print("day1 t-idx:", [base_dates[i] for i in p1[:8]], "...", [base_dates[i] for i in p1[-8:]])
p366 = pool_idx[366]
print("day366 t-idx:", [base_dates[i] for i in p366[:8]], "...", [base_dates[i] for i in p366[-8:]])

# Brute-force cross-check for random (D, cell)
import random
random.seed(42)
idx_of = {d: i for i, d in enumerate(base_dates)}
def brute_pool(D, cell):
    vals = []
    for y in range(1992, 2003):
        # find baseline date b with mdoy D in year y
        for (m, dd_), D2 in doy_table.items():
            if D2 == D:
                try: b = date(y, m, dd_)
                except ValueError: continue
                for k in range(-5, 6):
                    tt = b + timedelta(days=k)
                    if tt in idx_of:
                        v = SST[idx_of[tt], cell[0], cell[1]]
                        vals.append(v)
                break
    return np.array(vals, dtype='float64')

def hazen_p90(x):
    x = x[~np.isnan(x)]
    if x.size == 0: return np.nan
    return np.quantile(x, 0.9, method='hazen')

ok = True
for trial in range(200):
    D = random.choice(list(pool_idx.keys()))
    cell = (random.randrange(60), random.randrange(60))
    valsA = SST[np.array(pool_idx[D]), cell[0], cell[1]]
    valsB = brute_pool(D, cell)
    if valsA.shape != valsB.shape or not np.allclose(np.sort(valsA[~np.isnan(valsA)]), np.sort(valsB[~np.isnan(valsB)]), equal_nan=True):
        ok = False
        print("MISMATCH at D=", D, cell, valsA.shape, valsB.shape)
        break
print("brute-force cross-check (200 random):", "PASS" if ok else "FAIL")
pickle.dump({D: np.array(v, dtype=int) for D, v in pool_idx.items()}, open('/work/pool_idx.pkl','wb'))
