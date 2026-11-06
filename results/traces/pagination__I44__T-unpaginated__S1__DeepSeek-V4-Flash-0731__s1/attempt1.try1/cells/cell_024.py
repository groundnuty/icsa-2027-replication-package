from datetime import date, timedelta
import numpy as np
import pickle

# Reload data
with open('/tmp/work/all_loaded_dates.pkl', 'rb') as f:
    all_loaded_dates = pickle.load(f)

date_to_idx = {d: i for i, d in enumerate(all_loaded_dates)}

# Check: is Feb 29, 1992 in the pool for day 59?
# Day 59 = Feb 28
# Baseline dates with day 59: Feb 28 of 1992-2002
# Window for Feb 28, 1992: Feb 23 - Mar 4

# Check if Feb 29, 1992 is in our loaded dates
feb29_1992 = date(1992, 2, 29)
print(f"Feb 29, 1992 in loaded dates: {feb29_1992 in date_to_idx}")

# Now check if it's in the pool for day 59
# Build the pool for day 59
def month_day_to_doy(month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

def date_to_doy(d):
    return month_day_to_doy(d.month, d.day)

# Baseline dates with day 59
baseline_dates_59 = []
current = date(1992, 1, 1)
while current <= date(2002, 12, 31):
    if date_to_doy(current) == 59:
        baseline_dates_59.append(current)
    current += timedelta(days=1)

print(f"Baseline dates with day 59: {baseline_dates_59}")

# Check if Feb 29, 1992 is in the ±5 window of any of these
for bd in baseline_dates_59:
    for offset in range(-5, 6):
        pd = bd + timedelta(days=offset)
        if pd == feb29_1992:
            print(f"Feb 29, 1992 is in the window of {bd} (offset {offset})")

# Also check day 61
baseline_dates_61 = []
current = date(1992, 1, 1)
while current <= date(2002, 12, 31):
    if date_to_doy(current) == 61:
        baseline_dates_61.append(current)
    current += timedelta(days=1)

print(f"Baseline dates with day 61: {baseline_dates_61}")

for bd in baseline_dates_61:
    for offset in range(-5, 6):
        pd = bd + timedelta(days=offset)
        if pd == feb29_1992:
            print(f"Feb 29, 1992 is in the window of {bd} (offset {offset})")
