import numpy as np
from datetime import date
import h5py

z = np.load('/work/cubes.npz')
base_cube = z['base_cube']; targ_cube = z['targ_cube'].astype('float64')
base_ds = [date.fromisoformat(str(s)) for s in z['base_dates']]
targ_ds = [date.fromisoformat(str(s)) for s in z['targ_dates']]
sea_flat = np.load('/work/sea_flat.npy')
clim = np.load('/work/clim.npz'); thr_s = clim['thr_s']; clm_s = clim['clm_s']
CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335,366])
def md_doy(d): return int(CUM[d.month-1]+d.day)

c = 1018  # the closest-approach cell
cellvals = base_cube.reshape(len(base_ds), -1)[:, sea_flat][:, c].astype('float64')
ordmap = {d.toordinal(): i for i, d in enumerate(base_ds)}

def raw_pool(dd):
    seed = [d.toordinal() for d in base_ds if md_doy(d) == dd]
    idxs = set()
    for so in seed:
        for o in range(so-5, so+6):
            idxs.add(o)
    return np.array([cellvals[ordmap[o]] for o in sorted(idxs)])

def hazen(x):
    x = np.sort(x[np.isfinite(x)]); n = x.size
    h = n*0.9 + 0.5; lo = int(np.floor(h)); hi = int(np.ceil(h))
    return x[lo-1] if hi==lo else x[lo-1] + (h-lo)*(x[hi-1]-x[lo-1])

raws = {}
for dd in range(150, 261):
    if dd == 60: continue
    v = raw_pool(dd)
    raws[dd] = (hazen(v), v.mean())
raws[60] = (0.5*(raws[59][0]+raws[61][0]), 0.5*(raws[59][1]+raws[61][1]))

# target doys 153..244 -> smoothing window reaches 138..259; we have 150..260, enough for doys 165..244
targ_doy = np.array([md_doy(d) for d in targ_ds])
T = targ_cube.reshape(len(targ_ds), -1)[:, sea_flat]
diffs = []
max_err_thr = 0.0; max_err_clm = 0.0
for i in range(len(targ_ds)):
    dd = targ_doy[i]
    if not (165 <= dd <= 244): continue
    man_thr = np.mean([raws[(dd+off) % 366][0] for off in range(-15,16)])
    man_clm = np.mean([raws[(dd+off) % 366][1] for off in range(-15,16)])
    max_err_thr = max(max_err_thr, abs(man_thr - thr_s[dd-1, c]))
    max_err_clm = max(max_err_clm, abs(man_clm - clm_s[dd-1, c]))
    diffs.append(T[i, c] - thr_s[dd-1, c])
print('cell %d: max |manual - pipeline| threshold: %.2e ; climatology: %.2e' % (c, max_err_thr, max_err_clm))
print('cell %d: min(SST - thr) over checked days: %.6f' % (c, min(diffs)))

# independent check for a second cell, e.g. c=0 and c=1600
for cc in [0, 1600]:
    cv = base_cube.reshape(len(base_ds), -1)[:, sea_flat][:, cc].astype('float64')
    def rp(dd, cv=cv):
        seed = [d.toordinal() for d in base_ds if md_doy(d) == dd]
        idxs = set()
        for so in seed: idxs.update(range(so-5, so+6))
        return np.array([cv[ordmap[o]] for o in sorted(idxs)])
    rw = {}
    for dd in range(150, 261):
        if dd == 60: continue
        v = rp(dd); rw[dd] = (hazen(v), v.mean())
    rw[60] = (0.5*(rw[59][0]+rw[61][0]), 0.5*(rw[59][1]+rw[61][1]))
    e1 = max(abs(np.mean([rw[(targ_doy[i]+off)%366][0] for off in range(-15,16)]) - thr_s[targ_doy[i]-1, cc])
             for i in range(len(targ_ds)) if 165 <= targ_doy[i] <= 244)
    e2 = max(abs(np.mean([rw[(targ_doy[i]+off)%366][1] for off in range(-15,16)]) - clm_s[targ_doy[i]-1, cc])
             for i in range(len(targ_ds)) if 165 <= targ_doy[i] <= 244)
    print('cell %d: max |manual - pipeline|: thr %.2e, clm %.2e' % (cc, e1, e2))
