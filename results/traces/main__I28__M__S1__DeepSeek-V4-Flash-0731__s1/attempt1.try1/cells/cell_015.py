
import numpy as np
from datetime import date, timedelta

def doy_of_date(d):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month-1] + d.day

# Build pool dates for each doy
pool_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool = []
    for D in baseline_1992_2002:
        if doy_of_date(D) == doy:
            for k in range(-5, 6):
                X = D + timedelta(days=k)
                if X in date_to_idx:
                    pool.append(date_to_idx[X])
    pool_dates[doy] = np.array(pool)

# Compute threshold (90th percentile with Hazen method) and climatology (mean)
nlat, nlon = 60, 60
threshold = np.zeros((366, nlat, nlon), dtype=np.float64)
climatology = np.zeros((366, nlat, nlon), dtype=np.float64)

# Initialize with NaN for non-computed days
threshold[:] = np.nan
climatology[:] = np.nan

for doy in range(1, 367):
    if doy == 60:
        continue
    idxs = pool_dates[doy]
    pool_data = baseline_sst[idxs]  # (n_pool, nlat, nlon)
    
    # Compute per-cell: ignore NaN
    # Threshold: 90th percentile using Hazen method
    # We'll use numpy's percentile with method='hazen'
    for ilat in range(nlat):
        for ilon in range(nlon):
            vals = pool_data[:, ilat, ilon]
            valid = vals[np.isfinite(vals)]
            if len(valid) > 0:
                threshold[doy-1, ilat, ilon] = np.percentile(valid, 90, method='hazen')
                climatology[doy-1, ilat, ilon] = np.mean(valid)
            # else: stays NaN

print("Computed thresholds and climatologies for days 1-366 (except 60)")
# Check some values
print("Threshold at doy 153 (Jun 1), cell (0,0):", threshold[152, 0, 0])
print("Climatology at doy 153 (Jun 1), cell (0,0):", climatology[152, 0, 0])
print("Threshold at doy 60:", threshold[59, 0, 0])
print("Climatology at doy 60:", climatology[59, 0, 0])
