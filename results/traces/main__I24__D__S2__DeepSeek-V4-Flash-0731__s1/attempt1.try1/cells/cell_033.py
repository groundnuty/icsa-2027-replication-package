
import numpy as np
import pandas as pd

# Load baseline data
baseline_time = np.load('/work/baseline_time.npy', allow_pickle=True)
bt = pd.to_datetime(baseline_time)

# Load pool for doy 153 (Jun 1)
pool = np.load('/work/pool_153.npy')
pool_dates = bt[pool]
print("Pool for doy 153 (Jun 1):")
print("  Count:", len(pool_dates))
print("  First:", pool_dates[0])
print("  Last:", pool_dates[-1])
print("  All dates:", [d.strftime('%Y-%m-%d') for d in pool_dates])

# Check pool for doy 1 (Jan 1)
pool1 = np.load('/work/pool_1.npy')
pool1_dates = bt[pool1]
print("\nPool for doy 1 (Jan 1):")
print("  Count:", len(pool1_dates))
print("  First:", pool1_dates[0].strftime('%Y-%m-%d'))
print("  Last:", pool1_dates[-1].strftime('%Y-%m-%d'))
# Check if 1991-12-27 is in the pool
print("  1991-12-27 in pool:", pd.Timestamp('1991-12-27') in pool1_dates)

# Check pool for doy 366 (Dec 31)
pool366 = np.load('/work/pool_366.npy')
pool366_dates = bt[pool366]
print("\nPool for doy 366 (Dec 31):")
print("  Count:", len(pool366_dates))
print("  First:", pool366_dates[0].strftime('%Y-%m-%d'))
print("  Last:", pool366_dates[-1].strftime('%Y-%m-%d'))
# Check if 2003-01-05 is in the pool
print("  2003-01-05 in pool:", pd.Timestamp('2003-01-05') in pool366_dates)

# Check pool for doy 59 (Feb 28) - should include Feb 29 from leap years
pool59 = np.load('/work/pool_59.npy')
pool59_dates = bt[pool59]
print("\nPool for doy 59 (Feb 28):")
print("  Count:", len(pool59_dates))
# Check if Feb 29 of any leap year is in the pool
feb29_dates = [d for d in pool59_dates if d.month == 2 and d.day == 29]
print("  Feb 29 dates in pool:", [d.strftime('%Y-%m-%d') for d in feb29_dates])
