
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

# Load extended baseline data
ext_base_start = np.datetime64('1991-12-27')
ext_base_end = np.datetime64('2003-01-05')
ext_base_mask = (time >= ext_base_start) & (time <= ext_base_end)
ext_base_time_idx = np.where(ext_base_mask)[0]
ext_base_time = time[ext_base_time_idx]

ext_data = ds.analysed_sst.isel(time=ext_base_time_idx, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

def npdt_to_date(t):
    dt = t.astype('datetime64[D]').astype(object)
    return date(dt.year, dt.month, dt.day)

ext_dates = [npdt_to_date(t) for t in ext_base_time]

# Map date -> index in ext_data
date_to_idx = {d: i for i, d in enumerate(ext_dates)}

# Baseline dates
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)
baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append(d)
    d += timedelta(days=1)

# For each day of year, find the indices in ext_data that belong to its pool
doy_to_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    idx_set = set()
    for bd in baseline_dates:
        if doy_from_month_day(bd.month, bd.day) == doy:
            for offset in range(-5, 6):
                d2 = bd + timedelta(days=offset)
                if d2 in date_to_idx:
                    idx_set.add(date_to_idx[d2])
    doy_to_indices[doy] = sorted(idx_set)

# Verify counts
for doy in [1, 59, 61, 182, 366]:
    idxs = doy_to_indices[doy]
    print(f"Day {doy}: {len(idxs)} indices")

# Compute threshold and climatology for each cell and day-of-year
n_cells_lat = len(lat_idx)
n_cells_lon = len(lon_idx)
n_doy = 366

print("Computing thresholds and climatology...")

# Initialize arrays
threshold_raw = np.full((n_doy, n_cells_lat, n_cells_lon), np.nan)
climatology_raw = np.full((n_doy, n_cells_lat, n_cells_lon), np.nan)

for doy in range(1, 367):
    if doy == 60:
        continue
    idxs = doy_to_indices[doy]
    if len(idxs) == 0:
        print(f"Warning: Day {doy} has no indices!")
        continue
    pool = ext_data[idxs, :, :]  # (n_pool, n_lat, n_lon)
    
    # Compute 90th percentile (Hazen) and mean, ignoring NaN
    # For each cell
    for li in range(n_cells_lat):
        for loni in range(n_cells_lon):
            vals = pool[:, li, loni]
            good = ~np.isnan(vals)
            if good.any():
                threshold_raw[doy-1, li, loni] = np.quantile(vals[good], 0.9, method='hazen')
                climatology_raw[doy-1, li, loni] = np.mean(vals[good])
            else:
                threshold_raw[doy-1, li, loni] = np.nan
                climatology_raw[doy-1, li, loni] = np.nan

print("Done computing raw thresholds/climatology")

# Set day 60 to mean of days 59 and 61
threshold_raw[59, :, :] = (threshold_raw[58, :, :] + threshold_raw[60, :, :]) / 2.0
climatology_raw[59, :, :] = (climatology_raw[58, :, :] + climatology_raw[60, :, :]) / 2.0

print("Day 60 set to mean of days 59 and 61")
print("threshold shape:", threshold_raw.shape)
print("climatology shape:", climatology_raw.shape)

# Save these for later
np.save('/tmp/threshold_raw.npy', threshold_raw)
np.save('/tmp/climatology_raw.npy', climatology_raw)
np.save('/tmp/lat_idx.npy', lat_idx)
np.save('/tmp/lon_idx.npy', lon_idx)
print("Saved intermediate results")
