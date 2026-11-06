
import numpy as np
import datetime
from collections import defaultdict

# Re-run the full analysis from scratch to verify

# Load data
baseline_sst = np.load('/tmp/baseline_sst.npy')  # (4028, 60, 60)
target_sst = np.load('/tmp/target_sst.npy')       # (92, 60, 60)
baseline_times = np.load('/tmp/baseline_times.npy')
target_times = np.load('/tmp/target_times.npy')

baseline_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in baseline_times]
target_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in target_times]

def day_of_year(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Verify day_of_year for all baseline dates
print("Day-of-year verification:")
print(f"  1991-12-27: doy={day_of_year(datetime.date(1991,12,27))}")
print(f"  1992-01-01: doy={day_of_year(datetime.date(1992,1,1))}")
print(f"  1992-02-28: doy={day_of_year(datetime.date(1992,2,28))}")
print(f"  1992-02-29: doy={day_of_year(datetime.date(1992,2,29))}")
print(f"  1992-03-01: doy={day_of_year(datetime.date(1992,3,1))}")
print(f"  1993-03-01: doy={day_of_year(datetime.date(1993,3,1))}")
print(f"  2002-12-31: doy={day_of_year(datetime.date(2002,12,31))}")
print(f"  2003-01-05: doy={day_of_year(datetime.date(2003,1,5))}")
print(f"  2009-06-01: doy={day_of_year(datetime.date(2009,6,1))}")
print(f"  2009-08-31: doy={day_of_year(datetime.date(2009,8,31))}")
