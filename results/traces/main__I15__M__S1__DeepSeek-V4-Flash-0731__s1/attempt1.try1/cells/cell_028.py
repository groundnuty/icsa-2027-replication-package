import numpy as np
from datetime import datetime

# Load base dates
base_dates_str = np.load('/tmp/base_dates.npy')
base_dates = [datetime.strptime(s, '%Y%m%d') for s in base_dates_str]

print(f"First date: {base_dates[0]}")
print(f"Last date: {base_dates[-1]}")
print(f"Total: {len(base_dates)}")

# Check if extended window dates are present
check_dates = [
    datetime(1991, 12, 27),
    datetime(1991, 12, 31),
    datetime(1992, 1, 1),
    datetime(2002, 12, 31),
    datetime(2003, 1, 1),
    datetime(2003, 1, 5),
]

for d in check_dates:
    found = d in base_dates
    print(f"  {d.strftime('%Y-%m-%d')}: {'found' if found else 'NOT FOUND'}")
