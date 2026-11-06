import xarray as xr, numpy as np
ds = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
t = ds.time.values
print('time[0..2]:', t[:3], '...')
print('time[-2:]:', t[-2:], 'n=', len(t))
print('first/last:', str(t[0])[:10], str(t[-1])[:10])
print('mhw:', ds.mhw.dtype, dict(ds.mhw.sizes), 'sum:', int(ds.mhw.values.sum()))
print('land all zero:', int(ds.mhw.values[:, np.isnan(np.load('/tmp/tgt.npy')[0])].sum()) == 0)
print('lat[0],[−1]:', float(ds.lat[0]), float(ds.lat[-1]), '| lon[0],[−1]:', float(ds.lon[0]), float(ds.lon[-1]))
ds.close()
import os
print('files:', os.listdir('/work/output'))
