
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load saved data
baseline_sst = np.load('/work/baseline_sst.npy')
target_sst = np.load('/work/target_sst.npy')
baseline_time_int = np.load('/work/baseline_time.npy')
target_time_int = np.load('/work/target_time.npy')
lat_vals = np.load('/work/lat_vals.npy')
lon_vals = np.load('/work/lon_vals.npy')

# Convert time integers back to dates
baseline_dates = [pd.Timestamp(int(t)).date() for t in baseline_time_int]
target_dates = [pd.Timestamp(int(t)).date() for t in target_time_int]

print(f"Baseline dates: {baseline_dates[0]} to {baseline_dates[-1]}, count: {len(baseline_dates)}")
print(f"Target dates: {target_dates[0]} to {target_dates[-1]}, count: {len(target_dates)}")

# Day of year mapping function (1-366)
def day_of_year_366(d):
    m, day = d.month, d.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:m-1]) + day

# Identify sea cells: finite SST on every target day
sea_mask = np.all(~np.isnan(target_sst), axis=0)  # (60, 60)
print(f"Sea cells: {np.sum(sea_mask)} out of {sea_mask.size}")
