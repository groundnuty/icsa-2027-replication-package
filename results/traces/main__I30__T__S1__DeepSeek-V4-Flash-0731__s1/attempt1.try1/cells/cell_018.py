
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, date

# Load saved data
baseline_data = np.load('/tmp/baseline_data.npy')
target_data = np.load('/tmp/target_data.npy')
baseline_times = np.load('/tmp/baseline_times.npy').astype('datetime64[D]')
target_times = np.load('/tmp/target_times.npy').astype('datetime64[D]')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

print("baseline shape:", baseline_data.shape)
print("target shape:", target_data.shape)
print("baseline dtype:", baseline_data.dtype)
print("target dtype:", target_data.dtype)

# Convert to float64
baseline_data = baseline_data.astype(np.float64)
target_data = target_data.astype(np.float64)

# Day of year function
def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

# Compute day of year for each baseline time
baseline_doy = np.array([day_of_year(t.astype('datetime64[M]').astype(object).month, 
                                     t.astype('datetime64[D]').astype(object).day) 
                         for t in baseline_times])
print("baseline_doy range:", baseline_doy.min(), baseline_doy.max())
