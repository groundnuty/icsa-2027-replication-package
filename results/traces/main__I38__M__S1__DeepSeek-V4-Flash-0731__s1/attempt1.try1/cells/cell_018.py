
import numpy as np
from datetime import date, timedelta
import json, time

intermediate_dir = 'intermediate'

# Load metadata
with open(f'{intermediate_dir}/metadata.json') as f:
    meta = json.load(f)

baseline_dates = [date.fromisoformat(d) for d in meta['baseline_dates']]
target_dates = [date.fromisoformat(d) for d in meta['target_dates']]

# Load doy pool dates
with open(f'{intermediate_dir}/doy_pool_dates.json') as f:
    doy_pool_dates_str = json.load(f)
doy_to_pool_dates = {int(k): [date.fromisoformat(d) for d in v] for k, v in doy_pool_dates_str.items()}

# Load data
baseline_sst = np.load(f'{intermediate_dir}/baseline_sst.npy')
target_sst = np.load(f'{intermediate_dir}/target_sst.npy')
sea_cells = np.load(f'{intermediate_dir}/sea_cells.npy')

# Map baseline date to index
baseline_date_to_idx = {d: i for i, d in enumerate(baseline_dates)}

n_doy = 366
n_lat, n_lon = sea_cells.shape

# Compute thresholds and climatology for each doy
# threshold shape: (366, n_lat, n_lon)
# climatology shape: (366, n_lat, n_lon)
threshold = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)

t0 = time.time()
for doy in range(1, 367):
    if doy == 60:
        continue
    
    pool_dates = doy_to_pool_dates[doy]
    pool_indices = [baseline_date_to_idx[d] for d in pool_dates]
    
    # Extract pool: (n_pool, n_lat, n_lon)
    pool = baseline_sst[pool_indices].astype(np.float64)
    
    # For each cell, compute mean and 90th percentile ignoring NaN
    # Vectorize over cells
    for la in range(n_lat):
        for lo in range(n_lon):
            if not sea_cells[la, lo]:
                continue
            vals = pool[:, la, lo]
            valid = ~np.isnan(vals)
            n_valid = valid.sum()
            if n_valid > 0:
                v = vals[valid]
                threshold[doy-1, la, lo] = np.quantile(v, 0.9, method='hazen')
                climatology[doy-1, la, lo] = np.mean(v)
    
    if doy % 50 == 0:
        print(f"  Processed doy {doy}, elapsed: {time.time()-t0:.1f}s")

print(f"Threshold/climatology computation took {time.time()-t0:.1f}s")

# Set day 60 to mean of days 59 and 61
threshold[59] = (threshold[58] + threshold[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

np.save(f'{intermediate_dir}/threshold_raw.npy', threshold)
np.save(f'{intermediate_dir}/climatology_raw.npy', climatology)
print("Raw threshold/climatology saved")
