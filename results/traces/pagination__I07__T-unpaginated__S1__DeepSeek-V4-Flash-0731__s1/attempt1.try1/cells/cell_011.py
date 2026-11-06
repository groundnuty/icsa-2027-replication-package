
# Check for duplicates in doy pools
from collections import defaultdict
import datetime

def doy_from_date(date):
    month_starts = [1, 32, 61, 92, 122, 153, 183, 214, 245, 275, 306, 336]
    return month_starts[date.month - 1] + date.day - 1

ext_start = datetime.date(1991, 12, 27)
ext_end = datetime.date(2003, 1, 5)
base_start = datetime.date(1992, 1, 1)
base_end = datetime.date(2002, 12, 31)

ext_dates = []
d = ext_start
while d <= ext_end:
    ext_dates.append(d)
    d += datetime.timedelta(days=1)

base_dates = []
d = base_start
while d <= base_end:
    base_dates.append(d)
    d += datetime.timedelta(days=1)

doy_to_dates = defaultdict(list)
for X in ext_dates:
    for delta in range(-5, 6):
        Y = X + datetime.timedelta(days=delta)
        if base_start <= Y <= base_end:
            d = doy_from_date(Y)
            if d != 60:
                doy_to_dates[d].append(X)

# Check for duplicates
has_duplicates = False
for d, dates in doy_to_dates.items():
    if len(dates) != len(set(dates)):
        has_duplicates = True
        print(f"doy {d}: {len(dates)} dates but {len(set(dates))} unique")
print(f"Any duplicates: {has_duplicates}")

# Also check: does each doy pool contain all 121 unique dates?
for d in range(1, 367):
    if d != 60:
        if d in doy_to_dates and len(set(doy_to_dates[d])) != 121:
            print(f"doy {d}: {len(set(doy_to_dates[d]))} unique dates")
            break
print("All doys have 121 unique dates in pool")

# Save the mapping
import pickle
with open('/tmp/doy_to_dates.pkl', 'wb') as f:
    pickle.dump({d: [dt.strftime('%Y%m%d') for dt in dates] for d, dates in doy_to_dates.items()}, f)
print("Saved mapping")
