
import numpy as np

# Compute threshold and climatology for each day of year
# For each day of year d (except 60), pool_values[d] is a list of (lat, lon) arrays
# Convert to numpy arrays and compute

n_lat = 60
n_lon = 60

# Initialize arrays
threshold_raw = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology_raw = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

for d_doy in pool_values:
    if d_doy == 60:
        continue
    
    # Stack all values: (n_dates, n_lat, n_lon)
    stack = np.array(pool_values[d_doy], dtype=np.float64)  # (n_dates, 60, 60)
    
    # Compute threshold: 90th percentile using Hazen method, ignoring NaN
    # numpy.quantile with method='hazen'
    threshold_raw[d_doy-1] = np.nanquantile(stack, 0.9, axis=0, method='hazen')
    
    # Compute climatology: mean, ignoring NaN
    climatology_raw[d_doy-1] = np.nanmean(stack, axis=0)

print("Computed thresholds and climatology for baseline days")

# Check some values
print(f"Threshold for day 1, cell [30, 30]: {threshold_raw[0, 30, 30]:.4f}")
print(f"Climatology for day 1, cell [30, 30]: {climatology_raw[0, 30, 30]:.4f}")
print(f"Threshold for day 153 (Jun 1), cell [30, 30]: {threshold_raw[152, 30, 30]:.4f}")
print(f"Climatology for day 153 (Jun 1), cell [30, 30]: {climatology_raw[152, 30, 30]:.4f}")

# Check for NaN (all NaN in pool)
for d_doy in range(1, 367):
    if d_doy != 60:
        if np.isnan(threshold_raw[d_doy-1]).all():
            print(f"Day {d_doy}: all NaN threshold")
            break

# Check day 59 and 61 to set day 60
print(f"\nDay 59 threshold [30,30]: {threshold_raw[58, 30, 30]:.4f}")
print(f"Day 61 threshold [30,30]: {threshold_raw[60, 30, 30]:.4f}")
print(f"Day 59 clim [30,30]: {climatology_raw[58, 30, 30]:.4f}")
print(f"Day 61 clim [30,30]: {climatology_raw[60, 30, 30]:.4f}")
