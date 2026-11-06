import numpy as np
from datetime import date

z = np.load('/work/cubes.npz')
base_cube = z['base_cube']; targ_cube = z['targ_cube'].astype('float64')
base_ds = [date.fromisoformat(str(s)) for s in z['base_dates']]
targ_ds = [date.fromisoformat(str(s)) for s in z['targ_dates']]
sea_flat = np.load('/work/sea_flat.npy')
clim = np.load('/work/clim.npz'); thr_s = clim['thr_s']; clm_s = clim['clm_s']
CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335,366])
def md_doy(d): return int(CUM[d.month-1]+d.day)
ordmap = {d.toordinal(): i for i, d in enumerate(base_ds)}
targ_doy = np.array([md_doy(d) for d in targ_ds])
T = targ_cube.reshape(len(targ_ds), -1)[:, sea_flat]

def hazen(x):
    x = np.sort(x[np.isfinite(x)]); n = x.size
    h = n*0.9 + 0.5; lo = int(np.floor(h)); hi = int(np.ceil(h))
    return x[lo-1] if hi==lo else x[lo-1] + (h-lo)*(x[hi-1]-x[lo-1])

def check_cell(cc):
    cv = base_cube.reshape(len(base_ds), -1)[:, sea_flat][:, cc].astype('float64')
    def rp(dd):
        seed = [d.toordinal() for d in base_ds if md_doy(d) == dd]
        idxs = set()
        for so in seed: idxs.update(range(so-5, so+6))
        return np.array([cv[ordmap[o]] for o in sorted(idxs)])
    rw = {}
    for dd in range(138, 260):
        if dd == 60: continue
        v = rp(dd); rw[dd] = (hazen(v), v.mean())
    # no doy-60 involved for target doys 153..244 windows (138..259)
    e1 = max(abs(np.mean([rw[(targ_doy[i]+off)%366][0] for off in range(-15,16)]) - thr_s[targ_doy[i]-1, cc])
             for i in range(len(targ_ds)))
    e2 = max(abs(np.mean([rw[(targ_doy[i]+off)%366][1] for off in range(-15,16)]) - clm_s[targ_doy[i]-1, cc])
             for i in range(len(targ_ds)))
    mindiff = min(T[i, cc] - thr_s[targ_doy[i]-1, cc] for i in range(len(targ_ds)))
    return e1, e2, mindiff

for cc in [1018, 0, 1600, 3307]:
    e1, e2, md = check_cell(cc)
    print('cell %4d: max|manual-pipeline| thr %.2e clm %.2e ; min(SST-thr) over target = %.4f' % (cc, e1, e2, md))
