import fsspec, time
import xarray as xr
import numpy as np
print('numpy', np.__version__)
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z/s1z'
import datetime as dt
# benchmark 30 consecutive reads, region slice only
dates = [dt.date(2002,1,1)+dt.timedelta(days=i) for i in range(30)]
t0 = time.time()
vals = []
for d in dates:
    fn = root+f"/sst_{d:%Y%m%d}.nc"
    with fs.open(fn,'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        a = ds.analysed_sst.values
        vals.append(a[0])
    ds.close()
el = time.time()-t0
print('30 files in %.1fs -> %.2f s/file' % (el, el/30))
print('shape', np.array(vals).shape, 'dtype', np.array(vals).dtype)
print('time coord sample:', ds.time.values)