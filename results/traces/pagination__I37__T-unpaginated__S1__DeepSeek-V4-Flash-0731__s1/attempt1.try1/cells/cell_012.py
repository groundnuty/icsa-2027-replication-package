
import fsspec
import xarray as xr
import numpy as np
import datetime
import time

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Day of year mapping
def doy_from_date(date):
    month_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days[date.month-1] + date.day

# Build the list of baseline dates
baseline_start = datetime.date(1991, 12, 27)
baseline_end = datetime.date(2003, 1, 5)

baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append(d)
    d += datetime.timedelta(days=1)

# Build doy mapping for each baseline date
baseline_doy = {date: doy_from_date(date) for date in baseline_dates}

# Determine pool dates for each doy
doy_to_pool_dates = {i: set() for i in range(1, 367)}
for date in baseline_dates:
    if 1992 <= date.year <= 2002:
        d = doy_from_date(date)
        for offset in range(-5, 6):
            doy_to_pool_dates[d].add(date + datetime.timedelta(days=offset))

# Read all baseline data
print("Reading baseline data...")
start = time.time()

# Initialize storage
n_dates = len(baseline_dates)
baseline_sst = np.full((n_dates, 60, 60), np.nan, dtype=np.float64)
date_to_idx = {}

lat_idx = slice(330, 390)
lon_idx = slice(551, 611)

for i, date in enumerate(baseline_dates):
    date_to_idx[date] = i
    fname = f'sst_{date.year:04d}{date.month:02d}{date.day:02d}.nc'
    f = fs.open(f'{base}/{fname}', 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    baseline_sst[i] = ds.analysed_sst.values[0, lat_idx, lon_idx]
    ds.close()
    f.close()
    if (i+1) % 500 == 0:
        print(f"  Read {i+1}/{n_dates} files, elapsed: {time.time()-start:.1f}s")

print(f"Done reading {n_dates} baseline files in {time.time()-start:.1f}s")
print(f"Baseline SST shape: {baseline_sst.shape}")
print(f"NaN fraction: {np.isnan(baseline_sst).mean():.4f}")
