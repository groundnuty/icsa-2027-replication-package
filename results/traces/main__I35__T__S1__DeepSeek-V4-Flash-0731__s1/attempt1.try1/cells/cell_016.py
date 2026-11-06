
import numpy as np
import datetime

# Load data
baseline_sst = np.load('/tmp/baseline_sst.npy')  # (4028, 60, 60)
target_sst = np.load('/tmp/target_sst.npy')       # (92, 60, 60)
baseline_times = np.load('/tmp/baseline_times.npy')
target_times = np.load('/tmp/target_times.npy')

# Convert to dates
baseline_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in baseline_times]
target_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in target_times]

# Function to compute day-of-year (1-366) from a date
def day_of_year(dt):
    """Map date to day of year 1-366.
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366"""
    year = dt.year
    month = dt.month
    day = dt.day
    # Days in months before this month (for non-leap years)
    days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    doy = days_before[month-1] + day
    # Adjust for leap years
    if month > 2 and ((year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)):
        doy += 1
    return doy

# Test
print(f"1 Jan 1992: doy = {day_of_year(datetime.date(1992,1,1))}")
print(f"28 Feb 1992: doy = {day_of_year(datetime.date(1992,2,28))}")
print(f"29 Feb 1992: doy = {day_of_year(datetime.date(1992,2,29))}")
print(f"1 Mar 1992: doy = {day_of_year(datetime.date(1992,3,1))}")
print(f"31 Dec 1992: doy = {day_of_year(datetime.date(1992,12,31))}")
print(f"1 Jan 1993: doy = {day_of_year(datetime.date(1993,1,1))}")
print(f"28 Feb 1993: doy = {day_of_year(datetime.date(1993,2,28))}")
print(f"1 Mar 1993: doy = {day_of_year(datetime.date(1993,3,1))}")

# Check baseline dates
print(f"\nBaseline first date: {baseline_dates[0]}")
print(f"Baseline last date: {baseline_dates[-1]}")
print(f"Baseline day-of-years: {[day_of_year(d) for d in baseline_dates[:5]]}")
