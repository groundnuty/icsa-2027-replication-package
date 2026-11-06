
import numpy as np
import datetime

def day_of_year(date):
    y, m, d = date.year, date.month, date.day
    months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    doy = sum(months[:m-1]) + d
    if m > 2 and is_leap:
        doy += 1
    if not is_leap and m > 2:
        doy += 1
    return doy

# sst_data is a dict of date -> (60,60) array
# We need to compute threshold and climatology per cell per day-of-year

n_lat, n_lon = 60, 60

# For each doy 1-366 (excluding 60), find which dates contribute to the pool
baseline_start = datetime.date(1992, 1, 1)
baseline_end = datetime.date(2002, 12, 31)

# First, determine the pool dates for each doy
pool_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    centers = []
    dy = baseline_start
    while dy <= baseline_end:
        if day_of_year(dy) == doy:
            centers.append(dy)
        dy += datetime.timedelta(days=1)
    
    pool = []
    for c in centers:
        for k in range(-5, 6):
            x = c + datetime.timedelta(days=k)
            pool.append(x)
    pool_dates[doy] = pool

# Now compute threshold and climatology for each cell and doy
# threshold[doy-1] and clim[doy-1] are (60,60) arrays
threshold = np.zeros((366, n_lat, n_lon), dtype=np.float64)
clim = np.zeros((366, n_lat, n_lon), dtype=np.float64)

print('Computing thresholds and climatology...')

for doy in range(1, 367):
    if doy == 60:
        continue
    dates = pool_dates[doy]
    # Stack all values: (n_dates, n_lat, n_lon)
    values = np.array([sst_data[d] for d in dates], dtype=np.float64)
    
    # Compute 90th percentile ignoring NaN, method="hazen"
    # Need to do this cell by cell since NaN handling varies per cell
    for i in range(n_lat):
        for j in range(n_lon):
            col = values[:, i, j]
            valid = col[~np.isnan(col)]
            if len(valid) > 0:
                threshold[doy-1, i, j] = np.percentile(valid, 90, method='hazen')
                clim[doy-1, i, j] = np.mean(valid)
            else:
                threshold[doy-1, i, j] = np.nan
                clim[doy-1, i, j] = np.nan

print('Done computing thresholds and climatology')

# Set day 60 to mean of days 59 and 61
threshold[59] = (threshold[58] + threshold[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0

# Check for NaN in threshold/clim
print(f'NaN in threshold: {np.isnan(threshold).sum()}')
print(f'NaN in clim: {np.isnan(clim).sum()}')
