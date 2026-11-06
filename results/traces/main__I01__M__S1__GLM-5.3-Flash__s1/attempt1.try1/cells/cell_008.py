import os
print('cwd', os.getcwd())
os.makedirs('/tmp/testw', exist_ok=True); open('/tmp/testw/x','w').write('ok'); print('tmp writable')
os.makedirs('output', exist_ok=True); print('output dir ready', os.path.abspath('output'))
# sanity: lat/lon identical across files?
import xarray as xr, numpy as np
ds1 = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_19920601.nc', engine='h5netcdf')
for f in ['sst_19920101.nc','sst_20000630.nc','sst_20021231.nc','sst_20080831.nc']:
    ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/'+f, engine='h5netcdf')
    print(f, np.array_equal(ds.latitude.values, ds1.latitude.values), np.array_equal(ds.longitude.values, ds1.longitude.values), str(ds.time.values[0])[:10])
    ds.close()
