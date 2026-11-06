import numpy as np
from datetime import date

z = np.load('/work/cubes.npz')
base_cube = z['base_cube']; targ_cube = z['targ_cube'].astype('float64')
base_ds = [date.fromisoformat(str(s)) for s in z['base_dates']]
targ_ds = [date.fromisoformat(str(s)) for s in z['targ_dates']]
sea_flat = np.load('/work/sea_flat.npy')
CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335,366])
def md_doy(d): return int(CUM[d.month-1]+d.day)
ords = np.array([d.toordinal() for d in base_ds])
base_doy = np.array([md_doy(d) for d in base_ds])
targ_doy = np.array([md_doy(d) for d in targ_ds])
base_sea = base_cube.reshape(len(base_ds), -1)[:, sea_flat].astype('float64')
targ_sea = targ_cube.reshape(len(targ_ds), -1)[:, sea_flat]

pools = {}
for dd in range(1, 367):
    if dd == 60: continue
    seed_ord = ords[base_doy == dd]
    pools[dd] = np.where((np.abs(ords[:, None] - seed_ord[None, :]) <= 5).any(axis=1))[0]

def build_thr(method, smooth=True):
    nsea = base_sea.shape[1]
    thr = np.full((366, nsea), np.nan)
    for dd in range(1, 367):
        if dd == 60: continue
        vals = base_sea[pools[dd]]
        thr[dd-1] = np.nanquantile(vals, 0.9, axis=0, method=method)
    thr[59] = 0.5*(thr[58]+thr[60])
    if smooth:
        idx = (np.arange(366)[:, None] + np.arange(-15, 16)[None, :]) % 366
        thr = thr[idx].mean(axis=1)
    return thr

def report(name, thr):
    d = targ_sea - thr[targ_doy-1, :]
    nhot = int((d >= 0).sum())
    print('%-28s max(SST-thr)=%+.5f  hot days=%d' % (name, np.nanmax(d), nhot))
    return nhot

report('V1 hazen + wrap-smooth (spec)', build_thr('hazen'))
report('V2 hazen, no smoothing', build_thr('hazen', smooth=False))
report('V3 linear(type7) + smooth', build_thr('linear'))
report('V4 weibull(type6) + smooth', build_thr('weibull'))
report('V5 median_unbiased(type8)', build_thr('median_unbiased'))
