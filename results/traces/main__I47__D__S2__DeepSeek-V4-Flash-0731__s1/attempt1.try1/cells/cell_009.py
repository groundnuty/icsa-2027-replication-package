
import numpy as np
from datetime import date, timedelta

def day_of_year(month, day):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month-1]) + day
    return doy

# Convert epoch days to date objects
def date_from_epoch(days):
    return date(1970,1,1) + timedelta(days=int(days))

base_time = np.load('/work/base_time.npy')

# Baseline range: 1992-01-01 to 2002-12-31
baseline_start = (date(1992,1,1) - date(1970,1,1)).days
baseline_end = (date(2002,12,31) - date(1970,1,1)).days

# Build: for each date index i in base range, list of day-of-year pools it contributes to
# For each baseline date B with day-of-year d != 60, for offset -5..5, date D = B+offset contributes to pool d

n_base = len(base_time)
# pool_dates[d] = list of indices into base_time
pool_dates = {d: [] for d in range(1, 367) if d != 60}

for year in range(1992, 2003):
    for month in range(1, 13):
        if month == 2:
            # Feb has 29 days in the mapping; baseline dates are actual dates
            # In a non-leap year, Feb 29 doesn't exist
            pass
        # Determine days in this month for this actual year
        if month == 2:
            # check leap year
            if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                days_in_month = 29
            else:
                days_in_month = 28
        elif month in [4, 6, 9, 11]:
            days_in_month = 30
        else:
            days_in_month = 31
        for day in range(1, days_in_month+1):
            d = day_of_year(month, day)
            if d == 60:
                continue  # baseline Feb 29 dates don't define pools
            B = date(year, month, day)
            B_epoch = (B - date(1970,1,1)).days
            for offset in range(-5, 6):
                D_epoch = B_epoch + offset
                D = date_from_epoch(D_epoch)
                # Check D is within extended range
                if D_epoch >= base_time[0] and D_epoch <= base_time[-1]:
                    idx = int(D_epoch - base_time[0])
                    pool_dates[d].append(idx)

# Deduplicate
for d in pool_dates:
    pool_dates[d] = sorted(set(pool_dates[d]))

print("Pool sizes for various d:")
for d in [1, 59, 60, 61, 153, 244, 305, 366]:
    if d in pool_dates:
        print(f"d={d}: {len(pool_dates[d])} dates")
print("d=60 not in pool_dates:", 60 not in pool_dates)
