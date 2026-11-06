from datetime import datetime, timedelta

def day_of_year(date):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[date.month - 1] + date.day

# Check what day of year Jan 1, 2002 has
d = datetime(2002, 1, 1)
print(f"Jan 1, 2002 day of year: {day_of_year(d)}")

# Jan 1, 2002 + 4 days
print(f"Jan 1, 2002 + 4 = {d + timedelta(days=4)}")
# Jan 1, 2002 + 5 days
print(f"Jan 1, 2002 + 5 = {d + timedelta(days=5)}")

ext_start = datetime(1991, 12, 27)
ext_end = datetime(2003, 1, 5)

d4 = d + timedelta(days=4)
d5 = d + timedelta(days=5)
print(f"Jan 5, 2003 <= ext_end? {d4 <= ext_end}")
print(f"Jan 6, 2003 <= ext_end? {d5 <= ext_end}")

# Check all baseline dates with DOY 1
base_start = datetime(1992, 1, 1)
base_end = datetime(2002, 12, 31)
base_dates = []
dd = base_start
while dd <= base_end:
    if day_of_year(dd) == 1:
        base_dates.append(dd)
    dd += timedelta(days=1)

print(f"Baseline dates with DOY 1: {[d.strftime('%Y-%m-%d') for d in base_dates]}")

# For the last one (Jan 1, 2002), compute window
last_base = base_dates[-1]
print(f"Last baseline with DOY 1: {last_base}")
for offset in range(-5, 6):
    date = last_base + timedelta(days=offset)
    if ext_start <= date <= ext_end:
        print(f"  offset {offset}: {date.strftime('%Y-%m-%d')} (included)")
    else:
        print(f"  offset {offset}: {date.strftime('%Y-%m-%d')} (excluded)")
