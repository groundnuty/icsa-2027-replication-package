
import numpy as np
import datetime

# Verify pool construction for day 153 (June 1)
def day_of_year(dt):
    month_offsets = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[dt.month] + dt.day

# Check June 1, 1992 to 2002
for y in range(1992, 2003):
    dt = datetime.datetime(y, 6, 1)
    print(f"{dt.strftime('%Y-%m-%d')} -> doy {day_of_year(dt)}")

# Check window for June 1, 1992
d = datetime.datetime(1992, 6, 1)
print(f"\nWindow for June 1, 1992 (±5 days):")
for delta in range(-5, 6):
    x = d + datetime.timedelta(days=delta)
    print(f"  {x.strftime('%Y-%m-%d')}")
