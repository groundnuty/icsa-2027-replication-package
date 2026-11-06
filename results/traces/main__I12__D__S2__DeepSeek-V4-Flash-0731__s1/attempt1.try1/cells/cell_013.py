
import numpy as np
import pandas as pd
import xarray as xr
import json
import os

# Load data
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values
time = pd.to_datetime(ds.time.values)

lat_idx = np.where((lat >= 56.09) & (lat <= 57.29))[0]
lon_idx = np.where((lon >= 10.55) & (lon <= 11.75))[0]

# Baseline window
mask = (time >= pd.Timestamp('1991-12-27')) & (time <= pd.Timestamp('2003-01-05'))
idx_base = np.where(mask)[0]

# Target period
mask_t = (time >= pd.Timestamp('2009-06-01')) & (time <= pd.Timestamp('2009-08-31'))
idx_target = np.where(mask_t)[0]

base_time = time[idx_base]
target_time = time[idx_target]

base_sst = ds['analysed_sst'].isel(time=idx_base, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
target_sst = ds['analysed_sst'].isel(time=idx_target, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

# Step 1: Sea cells
n_lat, n_lon = 60, 60
sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_cells[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

print(f"Sea cells: {sea_cells.sum()}")

# Day of year mapping
def date_to_doy(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Build pools: for each doy d != 60, collect all SST values from dates within ±5 days
# of a baseline date (1992-01-01 to 2002-12-31) whose doy is d.
# The full date range for collecting is [1991-12-27, 2003-01-05].

full_base_time = base_time  # covers 1991-12-27 to 2003-01-05

base_dates_mask = (full_base_time >= pd.Timestamp('1992-01-01')) & (full_base_time <= pd.Timestamp('2002-12-31'))
base_dates = full_base_time[base_dates_mask]
base_doys = np.array([date_to_doy(d) for d in base_dates])

print(f"Baseline dates count: {len(base_dates)}")
print(f"Full window dates count: {len(full_base_time)}")

# For each doy d != 60, build the pool
n_doy = 366
# We'll build pool indices for each doy
pool_indices = {}  # doy -> array of indices into full_base_time (0-indexed into idx_base / base_time)

for d in range(1, n_doy + 1):
    if d == 60:
        continue
    # Find baseline dates with doy == d
    bd_mask = (base_doys == d)
    bd_dates = base_dates[bd_mask]
    
    if len(bd_dates) == 0:
        pool_indices[d] = np.array([], dtype=int)
        continue
    
    # Collect all dates within ±5 days of any baseline date with doy == d
    pool_date_set = set()
    for B in bd_dates:
        for delta in range(-5, 6):
            pool_date_set.add(B + pd.Timedelta(days=delta))
    
    # Map to indices in full_base_time
    indices = np.array([i for i, t in enumerate(full_base_time) if t in pool_date_set], dtype=int)
    pool_indices[d] = indices

# Verify pool sizes
print("\nPool sizes for selected doys:")
for d in [1, 2, 58, 59, 61, 62, 182, 365, 366]:
    if d in pool_indices:
        print(f"doy {d}: {len(pool_indices[d])} time points")
    else:
        print(f"doy {d}: empty/not found")

# Now compute threshold and climatology for each sea cell and each doy
print("\nComputing thresholds and climatology...")

# Initialize arrays
threshold = np.full((n_doy + 1, n_lat, n_lon), np.nan)  # index 1-366
climatology = np.full((n_doy + 1, n_lat, n_lon), np.nan)

# For each doy d != 60, compute threshold and climatology from pool
for d in range(1, n_doy + 1):
    if d == 60:
        continue
    idx = pool_indices[d]
    if len(idx) == 0:
        continue
    # Extract pool SST values: (n_dates, n_lat, n_lon)
    pool = base_sst[idx]  # shape (n_dates, n_lat, n_lon)
    
    # Compute per cell: 90th percentile (hazen method, ignoring NaN) and mean (ignoring NaN)
    for i in range(n_lat):
        for j in range(n_lon):
            if not sea_cells[i, j]:
                continue
            vals = pool[:, i, j]
            valid = vals[np.isfinite(vals)]
            if len(valid) == 0:
                continue
            threshold[d, i, j] = np.quantile(valid, 0.9, method='hazen')
            climatology[d, i, j] = np.mean(valid)

# Set day 60 as mean of days 59 and 61
threshold[60] = (threshold[59] + threshold[61]) / 2.0
climatology[60] = (climatology[59] + climatology[61]) / 2.0

print("Threshold and climatology computed for all doys.")

# Step 3: Smoothing - unweighted centred 31-day moving mean wrapping around the year
# For each sea cell, smooth threshold and climatology as 366-element arrays

print("\nSmoothing...")

def smooth_31day(arr):
    """Smooth a 366-element array with unweighted centred 31-day moving mean that wraps around."""
    # arr: shape (366,) or (366, n_lat, n_lon)
    if arr.ndim == 1:
        result = np.zeros_like(arr)
        for d in range(366):
            result[d] = np.mean(arr[(np.arange(d-15, d+16) % 366)])
        return result
    elif arr.ndim == 3:
        n_lat, n_lon = arr.shape[1], arr.shape[2]
        result = np.zeros_like(arr)
        for i in range(n_lat):
            for j in range(n_lon):
                result[:, i, j] = smooth_31day(arr[:, i, j])
        return result
    else:
        raise ValueError(f"Unsupported shape: {arr.shape}")

# Apply smoothing to threshold and climatology arrays (index 1-366)
# threshold has shape (367, n_lat, n_lon) where index 0 is unused
thresh_smoothed = np.full_like(threshold, np.nan)
clim_smoothed = np.full_like(climatology, np.nan)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        # Extract 366-element arrays (doy 1-366)
        t_arr = threshold[1:367, i, j]  # shape (366,)
        c_arr = climatology[1:367, i, j]
        
        # Smooth
        t_sm = smooth_31day(t_arr)
        c_sm = smooth_31day(c_arr)
        
        thresh_smoothed[1:367, i, j] = t_sm
        clim_smoothed[1:367, i, j] = c_sm

print("Smoothing done.")

# Step 3: Per-cell MHWs over target period
print("\nFinding per-cell MHWs...")

n_target = len(idx_target)

# For each target day, determine if it's hot for each sea cell
# Map target dates to doys
target_doys = np.array([date_to_doy(t) for t in target_time])
print("Target doys:", target_doys)

# Check hot days
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        for t_idx in range(n_target):
            d = target_doys[t_idx]
            sst_val = target_sst[t_idx, i, j]
            if np.isfinite(sst_val) and sst_val >= thresh_smoothed[d, i, j]:
                hot[t_idx, i, j] = True

print("Hot days computed.")

# Per-cell MHWs: runs of at least 5 consecutive hot days, join gaps of 1-2 non-hot days
# per-cell_mhw[t, i, j] = True if cell (i,j) is inside a per-cell MHW on target day t

per_cell_mhw = np.zeros((n_target, n_lat, n_lon), dtype=bool)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        h = hot[:, i, j]  # shape (n_target,)
        
        # Find runs of hot days
        # First identify consecutive hot runs
        runs = []
        in_run = False
        run_start = 0
        for t in range(n_target):
            if h[t]:
                if not in_run:
                    in_run = True
                    run_start = t
            else:
                if in_run:
                    runs.append((run_start, t - 1))
                    in_run = False
        if in_run:
            runs.append((run_start, n_target - 1))
        
        if len(runs) == 0:
            continue
        
        # Join runs separated by 1 or 2 non-hot days
        joined_runs = []
        current = runs[0]
        for r in runs[1:]:
            gap = r[0] - current[1] - 1
            if gap <= 2:
                # Join
                current = (current[0], r[1])
            else:
                joined_runs.append(current)
                current = r
        joined_runs.append(current)
        
        # Keep only runs of >= 5 consecutive hot days
        # (after joining, the total length including gaps should be >= 5)
        for (start, end) in joined_runs:
            if end - start + 1 >= 5:
                per_cell_mhw[start:end+1, i, j] = True

print("Per-cell MHWs computed.")

# Step 4: Regional events
# A day is active if at least one sea cell is inside a per-cell MHW on that day
active = np.zeros(n_target, dtype=bool)
for t in range(n_target):
    active[t] = np.any(per_cell_mhw[t])

print("Active days:", active.sum())

# Regional events: maximal runs of consecutive active days
events = []
in_event = False
event_start = 0
for t in range(n_target):
    if active[t]:
        if not in_event:
            in_event = True
            event_start = t
    else:
        if in_event:
            events.append((event_start, t - 1))
            in_event = False
if in_event:
    events.append((event_start, n_target - 1))

print("Regional events:", len(events))
for (s, e) in events:
    print(f"  Event: {target_time[s].strftime('%Y-%m-%d')} to {target_time[e].strftime('%Y-%m-%d')}")

# Write output
os.makedirs('output', exist_ok=True)

# mhw_mask.nc
# Create xarray dataset for mhw mask
# mhw has dimensions (time, lat, lon) covering region's grid cells and target days
region_lat = lat[lat_idx]
region_lon = lon[lon_idx]
target_time_np = ds.time.values[idx_target]

mhw_data = per_cell_mhw.astype(np.uint8)

ds_out = xr.Dataset(
    {
        'mhw': (('time', 'latitude', 'longitude'), mhw_data)
    },
    coords={
        'time': target_time_np,
        'latitude': region_lat,
        'longitude': region_lon,
    }
)

ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("\nWrote output/mhw_mask.nc")

# report.json
report = {
    'region': {
        'lat_min': 56.09,
        'lat_max': 57.29,
        'lon_min': 10.55,
        'lon_max': 11.75
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05'
    },
    'target_analysed': {
        'start': '2009-06-01',
        'end': '2009-08-31'
    },
    'events': [
        {'onset': target_time[s].strftime('%Y-%m-%d'), 'end': target_time[e].strftime('%Y-%m-%d')}
        for (s, e) in events
    ],
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Wrote output/report.json")
print("\nDone!")
