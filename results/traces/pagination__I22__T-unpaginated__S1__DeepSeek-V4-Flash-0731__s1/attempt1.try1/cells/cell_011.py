
import fsspec
import xarray as xr
import numpy as np
import datetime
import time
import os

os.makedirs('cache', exist_ok=True)

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Region indices
lat_idx = np.arange(196, 256)  # 60 cells
lon_idx = np.arange(485, 545)  # 60 cells

def day_of_year(date):
    y, m, d = date.year, date.month, date.day
    months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    doy = sum(months[:m-1]) + d
    if m > 2 and is_leap:
        doy += 1
    if not is_leap and m > 2:
        doy += 1
    return doy

# Build list of all dates to load
all_start = datetime.date(1991, 12, 27)
all_end = datetime.date(2003, 1, 5)

all_dates = []
d = all_start
while d <= all_end:
    all_dates.append(d)
    d += datetime.timedelta(days=1)

print(f'Total dates to load: {len(all_dates)}')

# Load all data
sst_data = {}
start_time = time.time()

for i, date in enumerate(all_dates):
    fname = f'sst_{date.strftime("%Y%m%d")}.nc'
    path = f'{base}/{fname}'
    with fs.open(path, 'rb') as fh:
        ds = xr.open_dataset(fh, engine='h5netcdf')
        sst = ds['analysed_sst'].values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].astype(np.float64)
        ds.close()
    sst_data[date] = sst
    if (i+1) % 1000 == 0:
        elapsed = time.time() - start_time
        print(f'Loaded {i+1}/{len(all_dates)} in {elapsed:.1f}s')

elapsed = time.time() - start_time
print(f'All {len(all_dates)} dates loaded in {elapsed:.1f}s')

# Save to cache
np.savez('cache/baseline_data.npz',
         **{date.strftime('%Y%m%d'): sst_data[date] for date in all_dates})
print('Saved to cache')

# Also save the date list
np.save('cache/baseline_dates.npy', np.array([d.toordinal() for d in all_dates]))
print('Saved dates')
