import numpy as np
from datetime import date
z = np.load('/work/cubes.npz')
targ_cube = z['targ_cube'].astype('float64')
targ_ds = [date.fromisoformat(str(s)) for s in z['targ_dates']]
sea_flat = np.load('/work/sea_flat.npy')
clim = np.load('/work/clim.npz')
thr_s = clim['thr_s']

T = targ_cube.reshape(len(targ_ds), -1)
targ_sea = T[:, sea_flat]
CUM = np.array([0,31,60,91,121,152,182,213,244,274,305,335,366])
targ_doy = np.array([CUM[d.month-1]+d.day for d in targ_ds])

print('target SST stats: min %.2f mean %.2f max %.2f' % (np.nanmin(targ_sea), np.nanmean(targ_sea), np.nanmax(targ_sea)))
print('thr at those doys: min %.2f mean %.2f max %.2f' % (thr_s[targ_doy-1].min(), thr_s[targ_doy-1].mean(), thr_s[targ_doy-1].max()))
c = 0
print('cell 0 first 10 days: SST', np.round(targ_sea[:10, c], 2), 'thr', np.round(thr_s[targ_doy[:10]-1, c], 2))
print('cell 0 all-time target max: %.2f, thr max over period: %.2f' % (np.nanmax(targ_sea[:, c]), thr_s[targ_doy-1, c].max()))
diff = targ_sea - thr_s[targ_doy-1, :]
print('SST - thr: min %.2f mean %.2f max %.2f' % (np.nanmin(diff), np.nanmean(diff), np.nanmax(diff)))
# check target cube is really 2017: re-read one file directly and compare
import h5py
with h5py.File('/data/icsa2027_data_20261101T090944Z/s1z/sst_20170715.nc','r') as f:
    v = f['analysed_sst'][0, 438:498, 487:547].astype('float64')
i15 = targ_ds.index(date(2017,7,15))
print('2017-07-15 re-read vs cached identical:', np.array_equal(np.nan_to_num(v,nan=-1), np.nan_to_num(targ_cube[i15],nan=-1)))
# check baseline cube is really 1992-2002: re-read
with h5py.File('/data/icsa2027_data_20261101T090944Z/s1z/sst_19980715.nc','r') as f:
    vb = f['analysed_sst'][0, 438:498, 487:547].astype('float64')
base_cube = z['base_cube']
base_ds = [date.fromisoformat(str(s)) for s in z['base_dates']]
ib = base_ds.index(date(1998,7,15))
print('1998-07-15 re-read vs cached identical:', np.array_equal(np.nan_to_num(vb,nan=-1), np.nan_to_num(base_cube[ib],nan=-1)))
print('baseline summer SST mean (Jul-Aug):', np.nanmean(base_cube[ [i for i,d in enumerate(base_ds) if d.month in (7,8)] ]))
print('target summer SST mean (Jul-Aug):', np.nanmean(targ_cube[ [i for i,d in enumerate(targ_ds) if d.month in (7,8)] ]))
