import numpy as np, collections, json
from datetime import date

z = np.load('/work/cubes.npz')
base_cube, targ_cube = z['base_cube'], z['targ_cube']
base_ds = [date.fromisoformat(str(s)) for s in z['base_dates']]
targ_ds = [date.fromisoformat(str(s)) for s in z['targ_dates']]
print('baseline', base_ds[0], base_ds[-1], len(base_ds), '| target', targ_ds[0], targ_ds[-1], len(targ_ds))

# month/day -> doy in 1..366 (Feb always 29 days; day 60 = 29 Feb)
CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335,366])
def md_doy(d): return int(CUM[d.month-1] + d.day)

# mapping tests
assert md_doy(date(2000,2,29)) == 60 and md_doy(date(1993,3,1)) == 61
assert md_doy(date(1992,12,31)) == 366 and md_doy(date(1992,1,1)) == 1
assert md_doy(date(2017,6,1)) == 153 and md_doy(date(2017,8,31)) == 244
assert md_doy(date(1991,12,27)) == 362 and md_doy(date(2003,1,5)) == 5
print('doy mapping tests OK')

base_doy = np.array([md_doy(d) for d in base_ds])
targ_doy = np.array([md_doy(d) for d in targ_ds])
print('target doys:', targ_doy[0], '..', targ_doy[-1])

ords = np.array([d.toordinal() for d in base_ds])
pools = {}
for dd in range(1, 367):
    if dd == 60: continue
    seed_ord = ords[base_doy == dd]
    memb = (np.abs(ords[:, None] - seed_ord[None, :]) <= 5).any(axis=1)
    pools[dd] = np.where(memb)[0]
sizes = {dd: len(p) for dd, p in pools.items()}
print('pool-size histogram:', dict(collections.Counter(sizes.values())))
print('sizes d=1..5:', [sizes[d] for d in range(1,6)], 'd=59:', sizes[59], 'd=61:', sizes[61],
      'd=180:', sizes[180], 'd=361..366:', [sizes[d] for d in range(361,367)])
# spot check: d=1 pool date range
p1 = pools[1]; p366 = pools[366]
print('d=1 pool dates:', base_ds[p1[0]], '..', base_ds[p1[-1]])
print('d=366 pool dates:', [str(base_ds[i]) for i in p366])

# sea cells: finite on every target day
targ64 = targ_cube.astype('float64')
sea2d = np.isfinite(targ64).all(axis=0)
nsea = int(sea2d.sum())
print('sea cells:', nsea, 'of', sea2d.size, '(land:', int((~sea2d).sum()), ')')
sea_flat = sea2d.ravel()
base_sea = base_cube.reshape(len(base_ds), -1)[:, sea_flat].astype('float64')
nan_per_cell = np.isnan(base_sea).sum(axis=0)
print('sea cells with baseline NaN:', int((nan_per_cell > 0).sum()), '| max NaN days in one cell:', int(nan_per_cell.max()))
np.save('/work/sea_flat.npy', sea_flat)
