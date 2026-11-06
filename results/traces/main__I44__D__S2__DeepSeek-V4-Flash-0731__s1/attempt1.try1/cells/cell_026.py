
import numpy as np
import pandas as pd

# Load data
baseline_data = np.load('/work/baseline_data.npy')
sea_cells = np.load('/work/sea_cells.npy')
thresholds = np.load('/work/thresholds.npy')
climatology = np.load('/work/climatology.npy')
thresholds_smooth = np.load('/work/thresholds_smooth.npy')
climatology_smooth = np.load('/work/climatology_smooth.npy')
mhw_mask = np.load('/work/mhw_mask.npy')

# Verify one specific computation
# Pick a sea cell
sea_cell_indices = np.argwhere(sea_cells)
lat_i, lon_i = sea_cell_indices[0]
print(f"Testing cell ({lat_i}, {lon_i})")

# Day of year function
def doy(month, day):
    offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return offsets[month-1] + day

def date_to_doy(dt):
    return doy(dt.month, dt.day)

# Build pool for doy 153 (Jun 1)
d = 153
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')
baseline_dates = pd.date_range(baseline_start, baseline_end, freq='D')
data_start = pd.Timestamp('1991-12-27')
data_end = pd.Timestamp('2003-01-05')
data_dates = pd.date_range(data_start, data_end, freq='D')

base_dates_d = [dt for dt in baseline_dates if date_to_doy(dt) == d]
print(f"Baseline dates with doy {d}: {[str(x.date()) for x in base_dates_d]}")

# Build pool
pool = set()
for t0 in base_dates_d:
    for offset in range(-5, 6):
        t = t0 + pd.Timedelta(days=offset)
        if data_start <= t <= data_end:
            pool.add(t)
pool = sorted(pool)
print(f"Pool size: {len(pool)}")
print(f"First few: {[str(x.date()) for x in pool[:5]]}")
print(f"Last few: {[str(x.date()) for x in pool[-5:]]}")

# Get values for this cell
date_to_pos = {dt: i for i, dt in enumerate(data_dates)}
positions = [date_to_pos[dt] for dt in pool]
values = baseline_data[positions, lat_i, lon_i]
valid = values[np.isfinite(values)]
print(f"Valid values: {len(valid)} out of {len(values)}")
print(f"Values range: {np.nanmin(valid):.2f} to {np.nanmax(valid):.2f}")

# Compute threshold and climatology
thresh_manual = np.percentile(valid, 90, method='hazen')
clim_manual = np.mean(valid)
print(f"Manual threshold: {thresh_manual:.4f}")
print(f"Manual climatology: {clim_manual:.4f}")
print(f"Stored threshold: {thresholds[lat_i, lon_i, d-1]:.4f}")
print(f"Stored climatology: {climatology[lat_i, lon_i, d-1]:.4f}")

# Verify they match
assert abs(thresh_manual - thresholds[lat_i, lon_i, d-1]) < 1e-10
assert abs(clim_manual - climatology[lat_i, lon_i, d-1]) < 1e-10
print("Manual and stored values match!")

# Verify day 60
print(f"\nDay 59 threshold: {thresholds[lat_i, lon_i, 58]:.4f}")
print(f"Day 60 threshold: {thresholds[lat_i, lon_i, 59]:.4f}")
print(f"Day 61 threshold: {thresholds[lat_i, lon_i, 60]:.4f}")
print(f"Expected day 60: {(thresholds[lat_i, lon_i, 58] + thresholds[lat_i, lon_i, 60]) / 2:.4f}")

# Verify smoothing
print(f"\nSmoothed threshold day 153: {thresholds_smooth[lat_i, lon_i, 152]:.4f}")
# Manual check: average of days 138-168 (indices 137-167)
indices = [(152 + offset) % 366 for offset in range(-15, 16)]
manual_smooth = np.mean(thresholds[lat_i, lon_i, indices])
print(f"Manual smooth: {manual_smooth:.4f}")
assert abs(thresholds_smooth[lat_i, lon_i, 152] - manual_smooth) < 1e-10
print("Smoothing verified!")
