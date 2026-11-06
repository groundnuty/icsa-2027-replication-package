
import xarray as xr
import numpy as np
from datetime import date, timedelta

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

time = ds.time.values
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 64.39) & (lat <= 65.59))[0]
lon_idx = np.where((lon >= 23.41) & (lon <= 24.61))[0]

# Day-of-year mapping
def doy_from_month_day(month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Baseline dates
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

# For each day-of-year, find the baseline dates that have that day-of-year
# and then all dates within ±5 days of them
baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append(d)
    d += timedelta(days=1)

# For each day of year d (1-366, excluding 60), find the pool of dates
# (not SST values yet - just the dates)
doy_to_dates = {}  # doy -> set of dates (as date objects)
for doy in range(1, 367):
    if doy == 60:
        continue
    dates_set = set()
    # Find baseline dates with this day-of-year
    for bd in baseline_dates:
        if doy_from_month_day(bd.month, bd.day) == doy:
            # Add all dates from bd-5 to bd+5
            for offset in range(-5, 6):
                dates_set.add(bd + timedelta(days=offset))
    doy_to_dates[doy] = sorted(dates_set)

# Check some sizes
for doy in [1, 59, 61, 182, 366]:
    dates = doy_to_dates[doy]
    print(f"Day {doy}: {len(dates)} dates, range {dates[0]} to {dates[-1]}")
