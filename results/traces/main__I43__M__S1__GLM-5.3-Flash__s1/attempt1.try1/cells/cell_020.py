import numpy as np
from datetime import date, timedelta
import h5py

z = np.load('/work/cubes.npz')
base_cube = z['base_cube']; targ_cube = z['targ_cube'].astype('float64')
base_ds = [date.fromisoformat(str(s)) for s in z['base_dates']]
targ_ds = [date.fromisoformat(str(s)) for s in z['targ_dates']]
sea_flat = np.load('/work/sea_flat.npy')
clim = np.load('/work/clim.npz'); thr_s = clim['thr_s']; clm_s = clim['clm_s']

CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335,366])
def md_doy(d): return int(CUM[d.month-1]+d.day)

# exact closest approach of SST to threshold
T = targ_cube.reshape(len(targ_ds), -1)[:, sea_flat]
targ_doy = np.array([md_doy(d) for d in targ_ds])
diff = T - thr_s[targ_doy-1, :]
mx = np.nanmax(diff)
loc = np.unravel_index(np.nanargmax(diff), diff.shape)
print('exact max(SST-thr) = %.10e at day idx %d (%s), cell %d' % (mx, loc[0], targ_ds[loc[0]], loc[1]))
print('count(diff >= 0):', int((diff >= 0).sum()), '| count(diff > -0.01):', int((diff > -0.01).sum()))
top5 = np.dstack(np.unravel_index(np.argsort(diff, axis=None)[-5:], diff.shape))[0]
for d_idx, c in top5[::-1]:
    print('  %s cell %d: SST %.4f thr %.4f diff %.6f' % (targ_ds[d_idx], c, T[d_idx,c], thr_s[targ_doy[d_idx]-1,c], diff[d_idx,c]))

# --- fully independent recomputation for one cell, explicit loops ---
c = loc[1]  # the closest cell
cellvals = base_cube.reshape(len(base_ds), -1)[:, sea_flat][:, c].astype('float64')  # (4028,)
ords = np.array([d.toordinal() for d in base_ds])
def raw_thr_for_doy(dd):
    pool = []
    for i, d in enumerate(base_ds):
        if md_doy(d) == 60:  # values still enter via calendar distance; doy-60 dates are 29 Feb
            pass
        if md_doy(d) == dd:
            pool.append(cellvals[i])
    # calendar-window membership: value enters if within 5 calendar days of any date with doy==dd
    seed = [d for d in base_ds if md_doy(d) == dd]
    idxs = set()
    for s in seed:
        for o in range(s.toordinal()-5, s.toordinal()+6):
            idxs.add(o)
    ordmap = {d.toordinal(): i for i, d in enumerate(base_ds)}
    vals = np.array([cellvals[ordmap[o]] for o in sorted(idxs)])
    return vals
def hazen(x):
    x = np.sort(x[np.isfinite(x)]); n = x.size
    h = n*0.9 + 0.5; lo = int(np.floor(h)); hi = int(np.ceil(h))
    return x[lo-1] if hi==lo else x[lo-1] + (h-lo)*(x[hi-1]-x[lo-1])

# raw (unsmoothed) p90 and mean for doys 140..170 for this cell; then smooth manually
raws = {}
for dd in range(125, 186):
    v = raw_thr_for_doy(dd)
    if dd == 60: continue
    raws[dd] = (hazen(v), v.mean())
# day 60 fill
raws[60] = (0.5*(raws[59][0]+raws[61][0]), 0.5*(raws[59][1]+raws[61][1]))
for target_doy in [targ_doy[loc[0]]]:
    manual = np.mean([raws[(target_doy+off) % 366][0] for off in range(-15,16)])
    print('cell %d doy %d: manual smoothed thr = %.6f | pipeline thr_s = %.6f' % (c, target_doy, manual, thr_s[target_doy-1, c]))
    manual_m = np.mean([raws[(target_doy+off) % 366][1] for off in range(-15,16)])
    print('cell %d doy %d: manual smoothed clim = %.6f | pipeline clm_s = %.6f' % (c, target_doy, manual_m, clm_s[target_doy-1, c]))
# pool stats at a doy
v = raw_thr_for_doy(170)
print('cell %d doy170 pool: n=%d mean=%.3f std=%.3f min=%.3f max=%.3f p90=%.3f' % (c, v.size, v.mean(), v.std(), v.min(), v.max(), hazen(v)))
