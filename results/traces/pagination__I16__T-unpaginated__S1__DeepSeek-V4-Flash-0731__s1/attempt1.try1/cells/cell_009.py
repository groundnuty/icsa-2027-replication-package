
from datetime import date, timedelta
import numpy as np
import fsspec
import xarray as xr
import time

# Region indices
lat_idx = slice(157, 217)  # 60 cells
lon_idx = slice(562, 622)  # 60 cells

# Extended baseline dates
baseline_start = date(1991, 12, 27)
baseline_end = date(2003, 1, 5)

dates = []
d = baseline_start
while d <= baseline_end:
    dates.append(d)
    d += timedelta(days=1)

n_dates = len(dates)
print(f'Total baseline dates: {n_dates}')

# Load all data
fs = fsspec.filesystem('onedata')
all_data = np.full((n_dates, 60, 60), np.nan, dtype=np.float64)
t0 = time.time()
for i, dt in enumerate(dates):
    fname = f'sst_{dt.year:04d}{dt.month:02d}{dt.day:02d}.nc'
    path = f'icsa2027_data_20261101T090944Z/s1z/{fname}'
    f = fs.open(path, 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    all_data[i] = ds['analysed_sst'].values[0, lat_idx, lon_idx].astype(np.float64)
    if (i+1) % 1000 == 0:
        print(f'Loaded {i+1}/{n_dates}, elapsed: {time.time()-t0:.1f}s')

print(f'Finished loading all baseline data in {time.time()-t0:.1f}s')
print(f'Shape: {all_data.shape}')
print(f'NaN fraction: {np.isnan(all_data).mean():.4f}')
np.save('/tmp/baseline_data.npy', all_data)
print('Saved to /tmp/baseline_data.npy')
