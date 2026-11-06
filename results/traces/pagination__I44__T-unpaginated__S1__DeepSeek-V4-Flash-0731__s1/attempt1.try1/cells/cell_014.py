import numpy as np
from datetime import date, timedelta
import pickle

# Load the saved data
baseline_sst = np.load('/tmp/work/baseline_sst.npy')
with open('/tmp/work/all_loaded_dates.pkl', 'rb') as f:
    all_loaded_dates = pickle.load(f)
region_lat = np.load('/tmp/work/region_lat.npy')
region_lon = np.load('/tmp/work/region_lon.npy')

n_days, n_lat, n_lon = baseline_sst.shape
print(f"baseline_sst: {baseline_sst.shape}")

# Day-of-year mapping function
def month_day_to_doy(month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

def date_to_doy(d):
    return month_day_to_doy(d.month, d.day)

# Build date -> index mapping
date_to_idx = {d: i for i, d in enumerate(all_loaded_dates)}

# Baseline dates: 1992-01-01 to 2002-12-31
baseline_dates = []
current = date(1992, 1, 1)
while current <= date(2002, 12, 31):
    baseline_dates.append(current)
    current += timedelta(days=1)

# Group baseline dates by day-of-year
doy_to_baseline_dates = {}
for bd in baseline_dates:
    d = date_to_doy(bd)
    if d not in doy_to_baseline_dates:
        doy_to_baseline_dates[d] = []
    doy_to_baseline_dates[d].append(bd)

# For each day-of-year d (1-366, excluding 60), build the pool indices
doy_to_pool_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    if d not in doy_to_baseline_dates:
        doy_to_pool_indices[d] = []
        continue
    
    pool_dates = set()
    for bd in doy_to_baseline_dates[d]:
        for offset in range(-5, 6):
            pd = bd + timedelta(days=offset)
            pool_dates.add(pd)
    
    idx = []
    for pd in pool_dates:
        if pd in date_to_idx:
            idx.append(date_to_idx[pd])
    
    doy_to_pool_indices[d] = sorted(idx)

# Verify all day-of-years have pool data
missing = [d for d in range(1, 367) if d != 60 and len(doy_to_pool_indices.get(d, [])) == 0]
print(f"Day-of-years with no pool: {missing}")

# Check some pool sizes
for d in [1, 59, 61, 153, 244, 366]:
    print(f"Day {d}: {len(doy_to_pool_indices[d])} pool dates")

# Compute threshold and climatology for each day-of-year and cell
# Initialize arrays (366 x n_lat x n_lon)
threshold = np.zeros((366, n_lat, n_lon), dtype=np.float64)
climatology = np.zeros((366, n_lat, n_lon), dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    
    pool_idx = doy_to_pool_indices[d]
    if len(pool_idx) == 0:
        continue
    
    # Extract pool values: (n_dates, n_lat, n_lon)
    pool = baseline_sst[pool_idx, :, :]
    
    # Compute 90th percentile per cell (Hazen method), ignoring NaN
    # np.nanquantile with method='hazen'
    thresh = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    clim = np.nanmean(pool, axis=0)
    
    threshold[d-1] = thresh
    climatology[d-1] = clim

# Handle day 60: mean of days 59 and 61
threshold[59] = (threshold[58] + threshold[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

# Check for cells where all values are NaN (land cells or no data)
# For land cells, the pool would be all NaN, so threshold/clim would be NaN
print(f"Threshold NaN count (day 1): {np.isnan(threshold[0]).sum()}")
print(f"Climatology NaN count (day 1): {np.isnan(climatology[0]).sum()}")

# Save intermediate results
np.save('/tmp/work/threshold_raw.npy', threshold)
np.save('/tmp/work/climatology_raw.npy', climatology)
print("Saved raw threshold and climatology.")

# Verify some values
print(f"Threshold day 153 cell [0,0]: {threshold[152,0,0]}")
print(f"Climatology day 153 cell [0,0]: {climatology[152,0,0]}")
