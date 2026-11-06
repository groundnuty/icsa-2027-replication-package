import numpy as np
from datetime import date, timedelta

z = np.load('/work/cubes.npz')
base_cube = z['base_cube']
base_ds = [date.fromisoformat(str(s)) for s in z['base_dates']]
sea_flat = np.load('/work/sea_flat.npy')
CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335,366])
def md_doy(d): return int(CUM[d.month-1]+d.day)

ords = np.array([d.toordinal() for d in base_ds])
base_doy = np.array([md_doy(d) for d in base_ds])
# baseline seeds: dates within 1992-01-01..2002-12-31
b0, b1 = date(1992,1,1).toordinal(), date(2002,12,31).toordinal()
is_seed = (ords >= b0) & (ords <= b1)
print('n baseline seeds:', int(is_seed.sum()), '(expect 4018 = 11 years incl 2000 leap, minus 1 leap day? -> 11*365+3)')
ext_dates = [d for d in base_ds if not (b0 <= d.toordinal() <= b1)]
print('extension dates:', [str(d) for d in ext_dates], 'their doys:', [md_doy(d) for d in ext_dates])

pools = {}
for dd in range(1, 367):
    if dd == 60: continue
    seed_ord = ords[is_seed & (base_doy == dd)]
    pools[dd] = np.where((np.abs(ords[:, None] - seed_ord[None, :]) <= 5).any(axis=1))[0]

import collections
sizes = {dd: len(p) for dd, p in pools.items()}
print('pool-size histogram:', dict(collections.Counter(sizes.values())))

def prange(dd):
    p = pools[dd]; ds = [base_ds[i] for i in p]
    # print contiguous segments
    segs = []; s = ds[0]; prev = ds[0]
    for d in ds[1:]:
        if (d - prev).days > 1:
            segs.append((s, prev)); s = d
        prev = d
    segs.append((s, prev))
    return segs

for dd in [1, 2, 5, 60, 362, 366]:
    if dd == 60:
        print('doy 60: no pool (filled later)'); continue
    segs = prange(dd)
    print('doy %3d pool: %d days, %d segments; first seg %s..%s, last seg %s..%s' %
          (dd, len(pools[dd]), len(segs), segs[0][0], segs[0][1], segs[-1][0], segs[-1][1]))
# doy-1 pool must NOT contain Dec 2002/Jan 2003; doy-366 pool must NOT contain Dec 1991 (beyond 27th)/Jan 1992
p1 = set(pools[1].tolist()); p366 = set(pools[366].tolist())
wrong1 = [str(base_ds[i]) for i in range(len(base_ds)) if base_ds[i] >= date(2002,12,27) and i in p1]
wrong366 = [str(base_ds[i]) for i in range(len(base_ds)) if base_ds[i] <= date(1992,1,6) and i in p366]
print('doy-1 pool wrongly incl. end-2002/2003 dates:', wrong1)
print('doy-366 pool wrongly incl. start-1992/1991 dates:', wrong366)
# doy-1 pool must include 1991-12-27..31; doy-366 must include 2003-01-01..05
print('doy-1 pool incl 1991-12-27..31:', all(str(base_ds[i]) in ['1991-12-27','1991-12-28','1991-12-29','1991-12-30','1991-12-31'] for i in range(5) if True) or [str(base_ds[i]) for i in pools[1][:6]])
print('doy-366 pool last 5 dates:', [str(base_ds[i]) for i in pools[366][-5:]])
np.save('/work/ord_is_seed.npy', is_seed)
