
import numpy as np
import pandas as pd

# Load data again if needed - let me keep it in memory by recomputing in the same cell
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values
time = pd.to_datetime(ds.time.values)

lat_idx = np.where((lat >= 56.09) & (lat <= 57.29))[0]
lon_idx = np.where((lon >= 10.55) & (lon <= 11.75))[0]

# Load baseline data: 1991-12-27 to 2003-01-05
t_start = pd.Timestamp('1991-12-27')
t_end = pd.Timestamp('2003-01-05')
mask = (time >= t_start) & (time <= t_end)
idx_base = np.where(mask)[0]

# Load target data: 2009-06-01 to 2009-08-31
t_start_t = pd.Timestamp('2009-06-01')
t_end_t = pd.Timestamp('2009-08-31')
mask_t = (time >= t_start_t) & (time <= t_end_t)
idx_target = np.where(mask_t)[0]

base_time = time[idx_base]
target_time = time[idx_target]

base_sst = ds['analysed_sst'].isel(time=idx_base, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
target_sst = ds['analysed_sst'].isel(time=idx_target, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

# Step 1: Identify sea cells - cells with finite SST on every day of target period
n_lat = len(lat_idx)
n_lon = len(lon_idx)
n_target = len(idx_target)

sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_cells[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

print(f"Number of sea cells: {sea_cells.sum()} out of {n_lat*n_lon}")

# Step 2: Build day-of-year mapping
def date_to_doy(dt):
    """Map date to day of year 1-366."""
    month = dt.month
    day = dt.day
    # Days in months before the month
    days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    return days_before[month-1] + day

# Let me verify: Jan 1 = 1, Feb 28 = 59, Feb 29 = 60, Mar 1 = 61, Dec 31 = 366
test_dates = [
    pd.Timestamp('2000-01-01'),  # should be 1
    pd.Timestamp('2000-02-28'),  # should be 59
    pd.Timestamp('2000-02-29'),  # should be 60
    pd.Timestamp('2000-03-01'),  # should be 61
    pd.Timestamp('2000-12-31'),  # should be 366
]
for d in test_dates:
    print(d.date(), "->", date_to_doy(d))
