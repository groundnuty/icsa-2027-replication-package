
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Verify day-of-year mapping
def day_of_year_366(d):
    m, day = d.month, d.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:m-1]) + day

print("Day-of-year mapping verification:")
print(f"  Jan 1: {day_of_year_366(date(2021, 1, 1))} (expected 1)")
print(f"  Feb 28: {day_of_year_366(date(2021, 2, 28))} (expected 59)")
print(f"  Feb 29: {day_of_year_366(date(2020, 2, 29))} (expected 60)")
print(f"  Mar 1: {day_of_year_366(date(2021, 3, 1))} (expected 61)")
print(f"  Jun 1: {day_of_year_366(date(2021, 6, 1))} (expected 153)")
print(f"  Aug 31: {day_of_year_366(date(2021, 8, 31))} (expected 244)")
print(f"  Dec 31: {day_of_year_366(date(2021, 12, 31))} (expected 366)")

# Check the day 59/61/60 values for a specific cell
smooth_thresholds = np.load('/work/smooth_thresholds.npy')
print(f"\nDay 59 threshold: {smooth_thresholds[58, 0, 0]}")
print(f"Day 60 threshold: {smooth_thresholds[59, 0, 0]}")
print(f"Day 61 threshold: {smooth_thresholds[60, 0, 0]}")

# Before smoothing, day 60 should be mean of days 59 and 61
thresholds = np.load('/work/thresholds.npy')
print(f"\nBefore smoothing:")
print(f"  Day 59: {thresholds[58, 0, 0]}")
print(f"  Day 60: {thresholds[59, 0, 0]}")
print(f"  Day 61: {thresholds[60, 0, 0]}")
print(f"  Mean(59,61): {(thresholds[58, 0, 0] + thresholds[60, 0, 0]) / 2}")

# Check the MHW detection for a specific cell
# Verify the runs and joins
mhw_mask = np.load('/work/mhw_mask.npy')
hot = np.load('/work/hot.npy')

# Let me check cell (0, 0)
print(f"\nCell (0,0) hot days: {np.where(hot[:, 0, 0])[0]}")
print(f"Cell (0,0) MHW days: {np.where(mhw_mask[:, 0, 0])[0]}")

# Find the sea cells
sea_mask = np.load('/work/sea_mask.npy')
print(f"\nSea mask sum: {sea_mask.sum()}")
print(f"Cell (0,0) is sea: {sea_mask[0, 0]}")

# Check a sea cell
sea_cells = np.argwhere(sea_mask)
print(f"First few sea cells: {sea_cells[:5]}")
