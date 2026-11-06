import numpy as np, datetime as dt, json, pickle

def doy(dd):
    """Spec mapping: 1..366 by month and day; 29 Feb -> 60; non-leap years have no day 60."""
    leap = dd.year % 4 == 0 and (dd.year % 100 != 0 or dd.year % 400 == 0)
    tt = dd.timetuple().tm_yday
    return tt + 1 if (not leap and dd.month > 2) else tt

tests = {
    dt.date(1992,1,1):1, dt.date(1992,2,28):59, dt.date(1992,2,29):60, dt.date(1992,3,1):61,
    dt.date(1992,12,30):365, dt.date(1992,12,31):366,
    dt.date(1993,2,28):59, dt.date(1993,3,1):61, dt.date(1993,12,31):366,
    dt.date(1993,3,15):75, dt.date(2000,2,29):60, dt.date(2000,3,1):61,
    dt.date(2021,6,1):153, dt.date(2021,6,30):182, dt.date(2021,7,1):183,
    dt.date(2021,8,31):244, dt.date(2021,12,31):366,
    dt.date(1991,12,27):362, dt.date(1991,12,31):366, dt.date(2003,1,5):5, dt.date(2003,1,1):1,
}
for k,v in tests.items():
    assert doy(k)==v, (k, doy(k), v)
print('doy mapping OK')

cache='/tmp/mhw_cache'
with open(f'{cache}/dates.json') as f:
    dates = [dt.date.fromisoformat(s) for s in json.load(f)]
nb = 4028
base_dates = dates[:nb]
print('read window:', base_dates[0], '..', base_dates[-1], '| target:', dates[nb], '..', dates[-1])

base_ord = np.array([dd.toordinal() for dd in base_dates], dtype=np.int64)
ref1992 = dt.date(1992,1,1)   # leap-year reference for doy -> (month, day)

pools = [None]*367
for d in range(1,367):
    if d == 60:
        continue
    r = ref1992 + dt.timedelta(days=d-1)
    centers = np.array([dt.date(y, r.month, r.day).toordinal() for y in range(1992,2003)], dtype=np.int64)
    m = ((base_ord[:,None] >= (centers-5)[None,:]) & (base_ord[:,None] <= (centers+5)[None,:])).any(axis=1)
    pools[d] = np.where(m)[0]

for d in [1,2,5,6,58,59,61,62,152,153,183,243,244,363,364,365,366]:
    idx = pools[d]
    print(f'doy {d:3d}: n={len(idx):3d}  {base_dates[idx[0]]} .. {base_dates[idx[-1]]}')

i1 = set(pools[1].tolist())
dec91 = [base_dates.index(dt.date(1991,12,x)) for x in range(27,32)]
print('doy1 includes 1991-12-27..31:', all(x in i1 for x in dec91))
i_jan5_2003 = base_dates.index(dt.date(2003,1,5))
print('2003-01-05 in doy1 pool:', i_jan5_2003 in i1, '| in doy5 pool:', i_jan5_2003 in set(pools[5].tolist()))
i_feb29 = base_dates.index(dt.date(1992,2,29))
print('Feb29-1992 in doy59:', i_feb29 in set(pools[59].tolist()),
      '| doy61:', i_feb29 in set(pools[61].tolist()),
      '| doy64:', i_feb29 in set(pools[64].tolist()),
      '| doy54:', i_feb29 in set(pools[54].tolist()))
sizes = sorted({len(pools[d]) for d in range(1,367) if d!=60})
print('pool sizes set:', sizes)
with open(f'{cache}/pools.pkl','wb') as f:
    pickle.dump(pools, f)
print('pools saved')