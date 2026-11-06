
import fsspec
import xarray as xr
import numpy as np
import datetime as dt
import time

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_start, lat_end = 260, 319
lon_start, lon_end = 485, 544

month_offsets = {1: 0, 2: 31, 3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}
def date_to_doy(y, m, d):
    return month_offsets[m] + d

# For cell (0,0), compute target SST for all target days
# Also compute the threshold for each target day's doy using the pool method

# First, identify the target doy values
target_start = dt.date(2017, 6, 1)
target_end = dt.date(2017, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += dt.timedelta(days=1)

# Load target SST for cell (0,0)
target_sst_cell = []
for date in target_dates:
    fname = f"sst_{date.year:04d}{date.month:02d}{date.day:02d}.nc"
    f = fs.open(f'{base_path}/{fname}', 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    val = float(ds.analysed_sst.values[0, lat_start, lon_start])
    ds.close()
    target_sst_cell.append(val)

target_doy = [date_to_doy(d.year, d.month, d.day) for d in target_dates]

# Now compute the threshold for each doy in the target period for cell (0,0)
# We need to load the pool data for each doy
# Let's compute for each doy in the target range (153-244)

# First, build the pool dates for each doy
baseline_dates_all = []
d = dt.date(1991, 12, 27)
while d <= dt.date(2003, 1, 5):
    baseline_dates_all.append(d)
    d += dt.timedelta(days=1)

# Get baseline dates with each doy (1992-2002)
doy_to_baseline = {}
for doy in range(1, 367):
    doy_to_baseline[doy] = []
d = dt.date(1992, 1, 1)
while d <= dt.date(2002, 12, 31):
    doy = date_to_doy(d.year, d.month, d.day)
    doy_to_baseline[doy].append(d)
    d += dt.timedelta(days=1)

# For each unique doy in the target period, compute the threshold
unique_target_doy = sorted(set(target_doy))
print(f"Unique target doy values: {unique_target_doy[0]} to {unique_target_doy[-1]}")
print(f"Count: {len(unique_target_doy)}")

# For cell (0,0), compute thresholds for a few representative doy values
# Let's compute for doy 153 (June 1), 183 (July 1), 213 (Aug 1), 244 (Aug 31)

def compute_threshold_for_cell(cell_idx_lat, cell_idx_lon, doy):
    """Compute threshold (MATLAB quantile) and climatology for a given cell and doy."""
    pool_dates = []
    for B in doy_to_baseline[doy]:
        for offset in range(-5, 6):
            pool_dates.append(B + dt.timedelta(days=offset))
    
    vals = []
    for date in pool_dates:
        fname = f"sst_{date.year:04d}{date.month:02d}{date.day:02d}.nc"
        f = fs.open(f'{base_path}/{fname}', 'rb')
        ds = xr.open_dataset(f, engine='h5netcdf')
        val = float(ds.analysed_sst.values[0, lat_start+cell_idx_lat, lon_start+cell_idx_lon])
        ds.close()
        vals.append(val)
    
    vals = np.array(vals)
    valid = vals[~np.isnan(vals)]
    if len(valid) == 0:
        return np.nan, np.nan, 0
    
    # MATLAB quantile (same as numpy linear)
    p = 0.9
    sorted_vals = np.sort(valid)
    n = len(sorted_vals)
    h = (n - 1) * p + 1  # 1-based
    idx = h - 1  # 0-based
    if idx == int(idx):
        q = sorted_vals[int(idx)]
    else:
        i0 = int(np.floor(idx))
        i1 = min(i0 + 1, n - 1)
        g = idx - i0
        q = (1 - g) * sorted_vals[i0] + g * sorted_vals[i1]
    
    mean = np.mean(valid)
    return q, mean, len(valid)

# Compute thresholds for a few doy values for cell (0,0)
cell = (0, 0)
for doy in [153, 158, 163, 168, 173, 178, 183, 188, 193, 198, 203, 208, 213, 218, 223, 228, 233, 238, 243, 244]:
    q, mean, cnt = compute_threshold_for_cell(cell[0], cell[1], doy)
    print(f"doy {doy}: threshold={q:.2f}, climatology={mean:.2f}, n={cnt}")

# Now print target SST for cell (0,0) at these doy values
print("\nTarget SST for cell (0,0):")
for i, (d, doy, sst) in enumerate(zip(target_dates, target_doy, target_sst_cell)):
    if doy in [153, 158, 163, 168, 173, 178, 183, 188, 193, 198, 203, 208, 213, 218, 223, 228, 233, 238, 243, 244]:
        print(f"  {d} (doy {doy}): {sst:.2f}")
