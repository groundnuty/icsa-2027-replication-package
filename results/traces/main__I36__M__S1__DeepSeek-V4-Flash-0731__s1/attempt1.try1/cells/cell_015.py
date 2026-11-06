
import numpy as np
from datetime import date, timedelta
import time

# Load data
baseline_data = np.load('/tmp/baseline_data.npy')
with open('/tmp/baseline_dates.txt') as f:
    baseline_dates = [date.fromisoformat(line.strip()) for line in f]

# Build date-to-index mapping
date_to_idx = {d: i for i, d in enumerate(baseline_dates)}

# Day of year functions
def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return d.day + sum(month_days[:d.month])

def doy_to_month_day(doy):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    for m in range(1, 13):
        if doy <= sum(month_days[:m+1]):
            return m, doy - sum(month_days[:m])
    return None

# For each doy d (except 60), find which dates contribute to its pool
# For each year y in 1992-2002:
#   b = date(y, m_d, dd_d)
#   Window: [b-5, b+5]
#   All dates in this window contribute to pool d

n_lat, n_lon = baseline_data.shape[1], baseline_data.shape[2]
n_cells = n_lat * n_lon

# Initialize threshold and climatology arrays (366, n_lat, n_lon)
threshold = np.zeros((366, n_lat, n_lon))
climatology = np.zeros((366, n_lat, n_lon))

start_time = time.time()
total_days_processed = 0

for doy in range(1, 367):
    if doy == 60:
        continue
    
    m, dd = doy_to_month_day(doy)
    
    # Collect all indices for this pool
    pool_indices = []
    for y in range(1992, 2003):
        try:
            b = date(y, m, dd)
        except ValueError:
            # Invalid date (e.g., Feb 29 in non-leap year for doy 60, but we skip doy 60)
            continue
        
        # Window [b-5, b+5]
        for t in range(-5, 6):
            d = b + timedelta(days=t)
            if d in date_to_idx:
                pool_indices.append(date_to_idx[d])
    
    if len(pool_indices) == 0:
        print(f"Warning: doy {doy} has empty pool")
        continue
    
    total_days_processed += len(pool_indices)
    
    # Get all SST values for this pool
    # Shape: (len(pool_indices), n_lat, n_lon)
    pool_data = baseline_data[pool_indices]  # float64
    
    # Compute threshold (90th percentile, numpy method="hazen") and climatology (mean)
    # per cell
    for i in range(n_lat):
        for j in range(n_lon):
            values = pool_data[:, i, j]
            valid = values[~np.isnan(values)]
            if len(valid) > 0:
                threshold[doy-1, i, j] = np.quantile(valid, 0.9, method='hazen')
                climatology[doy-1, i, j] = np.mean(valid)
            else:
                threshold[doy-1, i, j] = np.nan
                climatology[doy-1, i, j] = np.nan

    if doy % 30 == 0:
        elapsed = time.time() - start_time
        print(f"Processed doy {doy}/366, elapsed: {elapsed:.1f}s")

print(f"Total days in pools: {total_days_processed}")
print(f"Total time: {time.time()-start_time:.1f}s")

# Save threshold and climatology
np.save('/tmp/threshold_raw.npy', threshold)
np.save('/tmp/climatology_raw.npy', climatology)
print("Saved raw threshold and climatology")
