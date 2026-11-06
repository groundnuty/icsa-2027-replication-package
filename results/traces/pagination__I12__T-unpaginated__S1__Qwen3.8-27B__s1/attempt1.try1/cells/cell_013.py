import numpy as np
thr_raw = np.load('/tmp/thr_raw.npy'); thr_sm = np.load('/tmp/thr_sm.npy')
clim_raw = np.load('/tmp/clim_raw.npy'); clim_sm = np.load('/tmp/clim_sm.npy')
print('shapes', thr_raw.shape, thr_sm.shape, clim_raw.shape, clim_sm.shape)
t = np.load('/tmp/tgt.npz')
tgt = t['arr']
print('tgt', tgt.shape)
finite_tgt = np.all(np.isfinite(tgt), axis=0).reshape(3600)
sea = np.where(finite_tgt)[0]
print('sea cells:', len(sea), 'NaN in smoothed thr (sea):', bool(np.isnan(thr_sm[:, sea]).any()),
      'NaN in smoothed clim (sea):', bool(np.isnan(clim_sm[:, sea]).any()))
c = sea[0]
print('sample cell', c, 'flat idx in 60x60 -> (i,j) =', c//60, c%60)
import pickle
meta = pickle.load(open('/tmp/region_meta.pkl','rb'))
print('lat', float(meta['lat_vals'][c//60]), 'lon', float(meta['lon_vals'][c%60]))
for dd2 in (153, 198, 244):
    print(f'doy {dd2}: clim_raw={clim_raw[dd2-1,c]:.3f} thr_raw={thr_raw[dd2-1,c]:.3f} | clim_sm={clim_sm[dd2-1,c]:.3f} thr_sm={thr_sm[dd2-1,c]:.3f}')
print('target SST 2009-06-01 sample cell:', tgt[0, c//60, c%60])
# distribution sanity: June smoothed threshold range across sea cells
j = (153-1)
print('Jun1 thr_sm min/median/max (K):', np.nanmin(thr_sm[j,sea]), np.nanmedian(thr_sm[j,sea]), np.nanmax(thr_sm[j,sea]))
print('in C:', np.nanmin(thr_sm[j,sea])-273.15, np.nanmedian(thr_sm[j,sea])-273.15, np.nanmax(thr_sm[j,sea])-273.15)