
import numpy as np
import pickle
from datetime import date, timedelta

def day_of_year(month, day):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month-1]) + day
    return doy

base_data = np.load('/work/base_data.npy')  # (4028, 60, 60) float64
with open('/work/pool_dates.pkl', 'rb') as f:
    pool_dates = pickle.load(f)

n_lat = base_data.shape[1]
n_lon = base_data.shape[2]

# Initialize threshold and climatology arrays
threshold = np.zeros((366, n_lat, n_lon), dtype=np.float64)
climatology = np.zeros((366, n_lat, n_lon), dtype=np.float64)

# For each day-of-year d != 60, compute threshold and climatology
for d in range(1, 367):
    if d == 60:
        continue
    idx = np.array(pool_dates[d])
    pool = base_data[idx]  # (121, n_lat, n_lon)
    # Compute hazen 90th percentile ignoring NaN
    # Use nanpercentile with axis=0
    threshold[d-1] = np.nanpercentile(pool, 90, method='hazen', axis=0)
    climatology[d-1] = np.nanmean(pool, axis=0)

print("computed thresholds and climatology for d != 60")

# Set day 60 to mean of days 59 and 61 (0-indexed: 58 and 60)
threshold[59] = (threshold[58] + threshold[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

print("set day 60")
print("threshold shape", threshold.shape)
print("climatology shape", climatology.shape)

# Check for any remaining NaN in thresholds/climatology
print("NaN in threshold:", np.isnan(threshold).sum())
print("NaN in climatology:", np.isnan(climatology).sum())
