import numpy as np, datetime as dt, json
cache = '/tmp/mhw_cache'
cube = np.load(f'{cache}/cube.npy')  # (4120,60,60) float32
with open(f'{cache}/dates.json') as f:
    date_strs = json.load(f)
dates = [dt.date.fromisoformat(s) for s in date_strs]
nb = 4028
base_dates = dates[:nb]
base = cube[:nb].astype('float64')  # (4028,60,60)

# day-of-year mapping: 1..366 by month/day; 29 Feb -> 60; no day 60 in non-leap years
def doy(dd):
    if dd.month == 2 and dd.day == 29:
        return 60
    return dt.date(dd.year, dd.month, dd.day).timetuple().tm_yday

print('checks:', doy(dt.date(1992,1,1)), doy(dt.date(1992,2,28)), doy(dt.date(1992,2,29)),
      doy(dt.date(1992,3,1)), doy(dt.date(1993,12,31)))

# pool index lists: for each d in 1..366 (except 60), list of baseline indices whose
# |(base_date - pool_center_date)| <= 5 calendar days, pool_center has doy d, 1992..2002
def doy_to_cal(doy):
    # representative calendar date in year 2001 (non-leap) for mapping doy->month/day
    return dt.date(2001,1,1) + dt.timedelta(days=doy-1)

pool_idx = [[] for _ in range(367)]  # index 1..366 used (60 unused)
# precompute baseline doys array
bdoy = np.array([doy(dd) for dd in base_dates])

for ddoy in range(1, 367):
    if ddoy == 60:
        continue
    if ddoy == 59:
        centers = [dt.date(y,2,28) for y in range(1992,2003)]
    elif ddoy == 365:
        centers = [dt.date(y,12,30) for y in range(1992,2003)]
    elif ddoy == 366:
        centers = [dt.date(y,12,31) for y in range(1992,2003)]
    else:
        c = doy_to_cal(ddoy)
        centers = [dt.date(y, c.month, c.day) for y in range(1992, 2003)]
    idxs = []
    for c in centers:
        lo = c - dt.timedelta(days=5)
        hi = c + dt.timedelta(days=5)
        m = (bdoy_arr := None)  # placeholder
        for i, bd in enumerate(base_dates):
            if lo <= bd <= hi:
                idxs.append(i)
    idxs = np.array(sorted(idxs), dtype=int)
    pool_idx[ddoy] = idxs

for ddoy in [1, 2, 59, 61, 180, 181, 182, 183, 184, 243, 364, 365, 366]:
    print('doy', ddoy, 'pool size', len(pool_idx[ddoy]), 'first/last date:',
          base_dates[pool_idx[ddoy][0]], base_dates[pool_idx[ddoy][-1]])