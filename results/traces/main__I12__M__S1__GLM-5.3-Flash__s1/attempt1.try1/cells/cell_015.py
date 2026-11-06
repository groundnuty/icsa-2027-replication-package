import numpy as np, datetime as dt, os
dates = np.load('/tmp/dates.npy')
data = np.load('/tmp/sst_needed.npy')
n_base = 4028
base_dates = dates[:n_base]

md_doy = {}
cum = [0,31,59,90,120,151,181,212,243,273,304,334]
for m in range(1,13):
    for day in range(1,32):
        if not (m==2 and day>29) and not (m in (4,6,9,11) and day>30):
            md_doy[(m,day)] = cum[m-1] + day
md_doy[(2,29)] = 60
base_doy = np.array([md_doy[(int(str(d)[5:7]), int(str(d)[8:10]))] for d in base_dates])

# For each DOY d in 1..366, find all baseline-window indices with |doy(i) - d| <= 5
# (both doy in 1..366; pool for d=60 gets 29 Feb values + calendar neighbours)
pools = []
for d in range(1, 367):
    idx = np.where(np.abs(base_doy.astype(int) - d) <= 5)[0]
    pools.append(idx)
# expected pool sizes: base count + <=10 (or 11 crossing 59/60/61)
u,c = np.unique(base_doy, return_counts=True)
cnt_map = dict(zip(u.tolist(), c.tolist()))
for d in [1, 55, 59, 60, 61, 65, 100, 180, 240, 364, 365, 366]:
    base_n = cnt_map.get(d, 0)
    extra = {}
    for off in range(-5,6):
        if off==0: continue
        dd = d+off
        if dd < 1 or dd > 366: continue
        extra[dd] = cnt_map.get(dd, 0)
    exp = base_n + sum(extra.values())
    if d == 60:
        # DOY 61 doesn't exist in baseline (non-leap only) -> extra from 56..59,61..65 minus 61
        pass
    print(f'doy {d}: pool {len(pools[d-1])} (own {base_n}, extras {extra})')
