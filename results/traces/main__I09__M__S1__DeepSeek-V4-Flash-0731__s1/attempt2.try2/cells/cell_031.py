
import numpy as np
from datetime import date, timedelta

# Verify baseline date range and pool inclusion for edge cases

# Day-of-year mapping
month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
cum_days = [0]
for md in month_days[:-1]:
    cum_days.append(cum_days[-1] + md)

def date_to_doy(d):
    return cum_days[d.month - 1] + d.day

def doy_to_date_in_year(doy, year):
    for m in range(12):
        if doy <= cum_days[m] + month_days[m]:
            day = doy - cum_days[m]
            try:
                return date(year, m+1, day)
            except ValueError:
                return None
    return None

# Verify pool for doy 1 includes 1991-12-27
# Baseline dates with doy 1: Jan 1 of 1992-2002
# Pool: ±5 days around Jan 1 of each year
# Jan 1 1992 ±5 days: Dec 27 1991 to Jan 6 1992
doy1_base = doy_to_date_in_year(1, 1992)
print(f"doy 1 baseline date in 1992: {doy1_base}")
for offset in range(-5, 6):
    dd = doy1_base + timedelta(days=offset)
    print(f"  offset {offset}: {dd}")

# Verify pool for doy 366 includes 2003-01-05
doy366_base = doy_to_date_in_year(366, 2002)
print(f"\ndoy 366 baseline date in 2002: {doy366_base}")
for offset in range(-5, 6):
    dd = doy366_base + timedelta(days=offset)
    print(f"  offset {offset}: {dd}")

# Verify day 60 handling
# doy 59 = Feb 28, doy 60 = Feb 29, doy 61 = Mar 1
print(f"\ndoy 59: {doy_to_date_in_year(59, 1992)}")
print(f"doy 60: {doy_to_date_in_year(60, 1992)}")
print(f"doy 61: {doy_to_date_in_year(61, 1992)}")
print(f"doy 60 in non-leap 1993: {doy_to_date_in_year(60, 1993)}")

# Verify 29 Feb values belong to windows of neighbours
# Feb 29 1992 should be in pools of doys 55-65 (those whose baseline dates are within ±5 days)
feb29_1992 = date(1992, 2, 29)
print(f"\nFeb 29 1992 has doy: {date_to_doy(feb29_1992)}")

# Check which doys include Feb 29 in their pools
# For doy d, the baseline date in 1992 is doy_to_date_in_year(d, 1992)
# The window is ±5 days, so if Feb 29 is within ±5 days of that baseline date, it's in the pool
in_pool = []
for d in range(1, 367):
    if d == 60:
        continue
    d_base = doy_to_date_in_year(d, 1992)
    if d_base is None:
        continue
    if abs((d_base - feb29_1992).days) <= 5:
        in_pool.append(d)
print(f"Feb 29 1992 is in pools of doys: {in_pool}")
