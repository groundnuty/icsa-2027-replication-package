
from datetime import date, timedelta
import numpy as np
import fsspec
import xarray as xr
import time

# Region indices
lat_idx = slice(157, 217)  # 60 cells
lon_idx = slice(562, 622)  # 60 cells

# Target dates
target_start = date(2008, 6, 1)
target_end = date(2008, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)
n_target = len(target_dates)
print(f'Total target dates: {n_target}')

# Load target data
fs = fsspec.filesystem('onedata')
target_data = np.full((n_target, 60, 60), np.nan, dtype=np.float64)
t0 = time.time()
for i, dt in enumerate(target_dates):
    fname = f'sst_{dt.year:04d}{dt.month:02d}{dt.day:02d}.nc'
    path = f'icsa2027_data_20261101T090944Z/s1z/{fname}'
    f = fs.open(path, 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    target_data[i] = ds['analysed_sst'].values[0, lat_idx, lon_idx].astype(np.float64)

print(f'Finished loading target data in {time.time()-t0:.1f}s')
print(f'Shape: {target_data.shape}')
print(f'NaN fraction: {np.isnan(target_data).mean():.4f}')
np.save('/tmp/target_data.npy', target_data)
print('Saved target data')
