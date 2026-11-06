import numpy as np
from datetime import datetime, timedelta
import pickle

def day_of_year(date):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[date.month - 1] + date.day

# Load the pool dates
with open('/tmp/doy_pool_dates.pkl', 'rb') as f:
    doy_to_pool_dates = pickle.load(f)

# Check DOY 153 (Jun 1) - target period starts here
doy = 153
pool_dates = doy_to_pool_dates[doy]
print(f"DOY {doy} (Jun 1) pool dates: {len(pool_dates)}")
print(f"  First: {pool_dates[0].strftime('%Y-%m-%d')}")
print(f"  Last: {pool_dates[-1].strftime('%Y-%m-%d')}")

# These should be dates around Jun 1 of each year 1992-2002 (May 27 to Jun 6)
# Plus the extended windows
for d in pool_dates[:5]:
    print(f"  {d.strftime('%Y-%m-%d')} (DOY: {day_of_year(d)})")
print("  ...")
for d in pool_dates[-5:]:
    print(f"  {d.strftime('%Y-%m-%d')} (DOY: {day_of_year(d)})")
