
import numpy as np
pool_dates = np.load('/work/pool_dates.npy', allow_pickle=True).item() if False else None

# Let me just recompute pool_dates and check sizes
from datetime import date, timedelta

def day_of_year(month, day):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month-1]) + day
    return doy

base_time = np.load('/work/base_time.npy')
baseline_start = (date(1992,1,1) - date(1970,1,1)).days
baseline_end = (date(2002,12,31) - date(1970,1,1)).days

pool_dates = {d: [] for d in range(1, 367) if d != 60}

for year in range(1992, 2003):
    for month in range(1, 13):
        if month == 2:
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
                continue
            B = date(year, month, day)
            B_epoch = (B - date(1970,1,1)).days
            for offset in range(-5, 6):
                D_epoch = B_epoch + offset
                if D_epoch >= base_time[0] and D_epoch <= base_time[-1]:
                    idx = int(D_epoch - base_time[0])
                    pool_dates[d].append(idx)

sizes = {d: len(set(v)) for d, v in pool_dates.items()}
print("unique sizes:", set(sizes.values()))
print("total pools:", len(sizes))

# Save pool_dates
import pickle
with open('/work/pool_dates.pkl', 'wb') as f:
    pickle.dump(pool_dates, f)
print("saved pool_dates")
