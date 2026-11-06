
import xarray as xr
import numpy as np
from datetime import datetime, date, timedelta
from collections import defaultdict

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat_idx = list(range(34, 94))
lon_idx = list(range(213, 273))

time = ds['time'].values

# Load target data
target_start = np.datetime64('2014-06-01')
target_end = np.datetime64('2014-08-31')
target_mask = (time >= target_start) & (time <= target_end)
target_time_idx = np.where(target_mask)[0]
target_sst = ds['analysed_sst'].isel(time=target_time_idx, latitude=lat_idx, longitude=lon_idx).values

# Load baseline data
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
baseline_mask = (time >= baseline_start) & (time <= baseline_end)
baseline_time_idx = np.where(baseline_mask)[0]
baseline_sst = ds['analysed_sst'].isel(time=baseline_time_idx, latitude=lat_idx, longitude=lon_idx).values

# Sea cells: finite SST on every day of target period
sea_cells = ~np.isnan(target_sst).any(axis=0)
print("Sea cells:", sea_cells.sum())

# Day of year function
def day_of_year(month, day):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:month-1]) + day

# Map each baseline index to its date and day of year
baseline_dates = []
baseline_doy = []
for i in baseline_time_idx:
    t = time[i]
    dt = datetime.utcfromtimestamp(int(t) / 1e9)
    baseline_dates.append(dt.date())
    baseline_doy.append(day_of_year(dt.month, dt.day))

# For each doy d (1-366, except 60), determine which baseline indices belong to its pool
# Pool for d = union over baseline years of [date with doy d in that year - 5d, +5d]

# First, find for each baseline date, which doy pools it belongs to
# A date t belongs to pool d if t is within 5 days of a baseline date y (1992-01-01 to 2002-12-31) with doy(y) = d

# Let me compute which doy pools each baseline index belongs to
# Actually, let me compute which baseline indices belong to each doy pool

doy_to_pool_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    # Find all baseline dates (within 1992-01-01 to 2002-12-31) with this doy
    # and collect all indices within ±5 days
    pool_idx = []
    for idx, bd in enumerate(baseline_dates):
        d_bd = baseline_doy[idx]
        if d_bd == doy:
            # Check if this date is in 1992-01-01 to 2002-12-31
            if dt_date(1992, 1, 1) <= bd <= dt_date(2002, 12, 31):
                pool_idx.append(idx)
    doy_to_pool_indices[doy] = pool_idx

# Actually, I realize I need to be more careful. The pool for doy d consists of
# ALL dates t such that t is within 5 days of a baseline date y (1992-01-01 to 2002-12-31)
# with doy(y) = d.
# 
# But the baseline_dates array already covers 1991-12-27 to 2003-01-05, which includes the extended windows.
# So for doy d, I need to find all indices in baseline_dates whose date t satisfies:
# there exists y in [1992-01-01, 2002-12-31] with doy(y)=d and |t-y| <= 5 days.

# Let me redo this correctly.

from datetime import date as dt_date

# Generate all dates in 1992-01-01 to 2002-12-31 and group by doy
baseline_years = {}
d = dt_date(1992, 1, 1)
while d <= dt_date(2002, 12, 31):
    doy = day_of_year(d.month, d.day)
    if doy not in baseline_years:
        baseline_years[doy] = []
    baseline_years[doy].append(d)
    d += timedelta(days=1)

# For each doy d, the pool contains all dates t such that
# t in [y - 5d, y + 5d] for some y in baseline_years[d]
# These t dates are within 1991-12-27 to 2003-01-05

# For each doy d, find which indices in baseline_dates are in the pool
doy_to_pool_idx = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates_set = set()
    for y in baseline_years[doy]:
        for i in range(-5, 6):
            pool_dates_set.add(y + timedelta(days=i))
    
    # Find indices in baseline_dates that match pool dates
    idx_list = []
    for i, bd in enumerate(baseline_dates):
        if bd in pool_dates_set:
            idx_list.append(i)
    doy_to_pool_idx[doy] = idx_list

# Verify some pools
print("doy 1 pool size:", len(doy_to_pool_idx[1]))
print("doy 59 pool size:", len(doy_to_pool_idx[59]))
print("doy 61 pool size:", len(doy_to_pool_idx[61]))
print("doy 366 pool size:", len(doy_to_pool_idx[366]))

# Now for each sea cell, compute threshold (90th percentile) and climatology (mean) for each doy
# Convert target SST to float64 for computation
target_sst64 = target_sst.astype(np.float64)
baseline_sst64 = baseline_sst.astype(np.float64)

n_lat, n_lon = 60, 60
threshold = np.full((366, n_lat, n_lon), np.nan)
climatology = np.full((366, n_lat, n_lon), np.nan)

for doy in range(1, 367):
    if doy == 60:
        continue
    idx_list = doy_to_pool_idx[doy]
    # Extract pool values for all cells
    pool_data = baseline_sst64[idx_list]  # shape (n_pool, n_lat, n_lon)
    # For each cell, compute 90th percentile and mean ignoring NaN
    for li in range(n_lat):
        for lo in range(n_lon):
            if not sea_cells[li, lo]:
                continue
            vals = pool_data[:, li, lo]
            vals = vals[~np.isnan(vals)]
            if len(vals) > 0:
                threshold[doy, li, lo] = np.quantile(vals, 0.9, method='hazen')
                climatology[doy, li, lo] = np.mean(vals)

print("Computed thresholds and climatology for individual days")
print("Threshold NaN count:", np.isnan(threshold).sum())
print("Climatology NaN count:", np.isnan(climatology).sum())
