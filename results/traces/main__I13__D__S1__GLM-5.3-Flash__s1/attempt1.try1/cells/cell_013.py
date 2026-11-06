import h5py, numpy as np
f = h5py.File('/work/data/test_20210601.nc', 'r')
print(list(f.keys()))
dsvar = f['analysed_sst']
print('shape:', dsvar.shape, 'dtype:', dsvar.dtype)
print('attrs:', dict(dsvar.attrs))
lat = f['latitude'][:]
lon = f['longitude'][:]
print('lat dtype:', lat.dtype, 'first/last:', lat[0], lat[-1], 'step:', np.diff(lat.astype(np.float64))[:3])
print('lon dtype:', lon.dtype, 'first/last:', lon[0], lon[-1], 'step:', np.diff(lon.astype(np.float64))[:3])
print('time:', f['time'][:], dict(f['time'].attrs))
# check region
latr = lat.astype(np.float64); lonr = lon.astype(np.float64)
ilat = np.where((latr >= 56.09) & (latr <= 57.29))[0]
ilon = np.where((lonr >= 10.55) & (lonr <= 11.75))[0]
print('lat idx:', ilat[0], ilat[-1], 'n=', len(ilat), 'vals:', latr[ilat[0]], latr[ilat[-1]])
print('lon idx:', ilon[0], ilon[-1], 'n=', len(ilon), 'vals:', lonr[ilon[0]], lonr[ilon[-1]])
# sample of raw storage
print('raw sample:', dsvar[0, 130, 78], 'chunks:', dsvar.chunks, 'compression:', dsvar.compression)
# check if scale/offset present at raw level
import json
f.close()
