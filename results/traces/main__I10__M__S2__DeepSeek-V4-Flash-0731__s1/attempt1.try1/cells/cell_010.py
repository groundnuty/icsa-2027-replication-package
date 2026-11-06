
from datetime import date, timedelta

# Check dates in pool 59
pool_dates_actual = []
d = date(1991, 12, 27)
while d <= date(2003, 1, 5):
    pool_dates_actual.append(d)
    d += timedelta(days=1)

# Print pool 59 dates
doy_to_pool_dates = {}
for pi, t in enumerate(pool_dates_actual):
    for offset in range(-5, 6):
        b = t + timedelta(days=offset)
        if b >= date(1992,1,1) and b <= date(2002,12,31):
            # compute doy
            months = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            dd = sum(months[:b.month-1]) + b.day
            if dd == 59 and dd != 60:
                doy_to_pool_dates.setdefault(59, set()).add(t)

print("Pool 59 dates (first year):")
dates_59 = sorted(doy_to_pool_dates[59])
for t in dates_59:
    if t.year == 1992:
        print(" ", t)

# Check pool 1 dates
print("\nPool 1 dates:")
for pi, t in enumerate(pool_dates_actual):
    for offset in range(-5, 6):
        b = t + timedelta(days=offset)
        if b >= date(1992,1,1) and b <= date(2002,12,31):
            months = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            dd = sum(months[:b.month-1]) + b.day
            if dd == 1:
                doy_to_pool_dates.setdefault(1, set()).add(t)

dates_1 = sorted(doy_to_pool_dates[1])
print("All pool 1 dates:")
for t in dates_1:
    if t.year in (1991, 1992, 1993, 2002, 2003):
        print(" ", t)
