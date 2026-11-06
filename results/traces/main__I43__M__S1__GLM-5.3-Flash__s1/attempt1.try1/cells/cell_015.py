import numpy as np
from datetime import date

z = np.load('/work/cubes.npz')
base_cube = z['base_cube']
base_ds = [date.fromisoformat(str(s)) for s in z['base_dates']]

CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335,366])
def md_doy(d): return int(CUM[d.month-1] + d.day)

sea_flat = np.load('/work/sea_flat.npy')
base_sea = base_cube.reshape(len(base_ds), -1)[:, sea_flat].astype('float64')
ords = np.array([d.toordinal() for d in base_ds])
base_doy = np.array([md_doy(d) for d in base_ds])

pools = {}
for dd in range(1, 367):
    if dd == 60: continue
    seed_ord = ords[base_doy == dd]
    pools[dd] = np.where((np.abs(ords[:, None] - seed_ord[None, :]) <= 5).any(axis=1))[0]

nsea = base_sea.shape[1]
thr = np.full((366, nsea), np.nan)
clm = np.full((366, nsea), np.nan)
for dd in range(1, 367):
    if dd == 60: continue
    vals = base_sea[pools[dd]]
    thr[dd-1] = np.nanquantile(vals, 0.9, axis=0, method='hazen')
    clm[dd-1] = np.nanmean(vals, axis=0)
print('computed; thr finite:', np.isfinite(thr).all(), 'clm finite:', np.isfinite(clm).all())

thr[59] = 0.5*(thr[58] + thr[60])
clm[59] = 0.5*(clm[58] + clm[60])

idx = (np.arange(366)[:, None] + np.arange(-15, 16)[None, :]) % 366
def circ_smooth31(a): return a[idx].mean(axis=1)

# brute-force verification of smoothing
def brute(a):
    out = np.empty_like(a)
    for d in range(366):
        out[d] = sum(a[(d+off) % 366] for off in range(-15,16)) / 31.0
    return out
rng = np.random.default_rng(1)
t = rng.normal(size=(366, 4))
print('smooth max diff vs brute force:', np.abs(circ_smooth31(t) - brute(t)).max())

thr_s = circ_smooth31(thr)
clm_s = circ_smooth31(clm)
np.savez_compressed('/work/clim.npz', thr_s=thr_s, clm_s=clm_s)
print('saved clim.npz')
print('sample cell0: doy170 clim %.3f thr %.3f | doy230 clim %.3f thr %.3f' %
      (clm_s[169,0], thr_s[169,0], clm_s[229,0], thr_s[229,0]))
print('region-avg summer (doy 200): clim %.3f thr %.3f' % (clm_s[199].mean(), thr_s[199].mean()))
print('seasonal cycle sanity: doy15 vs doy200 region-avg clim:', round(clm_s[14].mean(),3), round(clm_s[199].mean(),3))
