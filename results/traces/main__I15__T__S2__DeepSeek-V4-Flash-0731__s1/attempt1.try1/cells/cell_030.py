
import numpy as np
import pandas as pd
from datetime import date, timedelta
import pickle

# Re-verify the DOY mapping
def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Verify DOY mapping for key dates
test_dates = [
    (date(2019, 1, 1), 1),
    (date(2019, 2, 28), 59),
    (date(2019, 3, 1), 61),
    (date(2019, 6, 1), 153),
    (date(2019, 8, 31), 244),
    (date(2019, 12, 31), 366),
    (date(2020, 2, 29), 60),  # leap year
]
for d, expected in test_dates:
    result = day_of_year(d)
    status = '✓' if result == expected else '✗'
    print(f'{status} {d}: DOY={result}, expected={expected}')

# Verify pool construction for DOY=153 (June 1)
print('\nPool verification for DOY=153 (June 1):')
# Baseline dates with DOY=153
# June 1 of each year 1992-2002
# Let's check
pools = pickle.load(open('pools.pkl', 'rb'))
pool_153 = pools[153]
print(f'  Pool size: {len(pool_153)}')

# Load base_time to check dates
base_time = np.load('base_time.npy').astype('datetime64[D]').astype('datetime64[ns]')
for idx in pool_153[:12]:
    print(f'  {pd.Timestamp(base_time[idx]).strftime("%Y-%m-%d")}')
