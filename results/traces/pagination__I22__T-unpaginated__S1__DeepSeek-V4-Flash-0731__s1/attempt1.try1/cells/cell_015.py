
import fsspec
import xarray as xr
import numpy as np
import datetime
import time

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

lat_idx = np.arange(196, 256)
lon_idx = np.arange(485, 545)

# Target period
target_start = datetime.date(2004, 6, 1)
target_end = datetime.date(2004, 8, 31)

target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += datetime.timedelta(days=1)

print(f'Target dates: {len(target_dates)} from {target_dates[0]} to {target_dates[-1]}')

# Load target data
target_sst = {}
start_time = time.time()
for i, date in enumerate(target_dates):
    fname = f'sst_{date.strftime("%Y%m%d")}.nc'
    path = f'{base}/{fname}'
    with fs.open(path, 'rb') as fh:
        ds = xr.open_dataset(fh, engine='h5netcdf')
        sst = ds['analysed_sst'].values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].astype(np.float64)
        ds.close()
    target_sst[date] = sst

elapsed = time.time() - start_time
print(f'Target data loaded in {elapsed:.1f}s')

# Save target data
np.savez('cache/target_data.npz',
         **{date.strftime('%Y%m%d'): target_sst[date] for date in target_dates})
np.save('cache/target_dates.npy', np.array([d.toordinal() for d in target_dates]))
print('Saved target data')
