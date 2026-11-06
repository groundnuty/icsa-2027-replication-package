
from datetime import datetime, timedelta

target_start = datetime(2014, 6, 1)
target_end = datetime(2014, 8, 31)
n_days = (target_end - target_start).days + 1
print(f"Target days: {n_days}")

# Generate all target dates
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)
print(f"First target date: {target_dates[0]}")
print(f"Last target date: {target_dates[-1]}")

# For each target date, compute day of year
starts = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
for td in target_dates[:5]:
    d_doy = starts[td.month] + td.day
    print(f"{td.date()}: doy={d_doy}")
