# Check the last dates for DOY 1 and DOY 366
from datetime import datetime, timedelta

# Verify the DOY 1 pool
doy1_dates = doy_to_pool_dates[1]
print(f"DOY 1 last few dates: {doy1_dates[-5:]}")

# Verify: Jan 1, 2002 + 5 = Jan 6, 2003, but ext_end is Jan 5, 2003
# So Jan 6 should be excluded
print("Jan 6, 2003 in pool?", datetime(2003, 1, 6) in doy1_dates)

# Check DOY 366 (Dec 31)
doy366_dates = doy_to_pool_dates[366]
print(f"DOY 366 last few: {doy366_dates[-5:]}")
print("Dec 31, 2002 + 5 = Jan 5, 2003, in pool?", datetime(2003, 1, 5) in doy366_dates)
print("Jan 6, 2003 in pool?", datetime(2003, 1, 6) in doy366_dates)

# Check DOY 365 (Dec 30) - its window should reach Jan 4, 2003
doy365_dates = doy_to_pool_dates[365]
print(f"DOY 365 last few: {doy365_dates[-5:]}")
