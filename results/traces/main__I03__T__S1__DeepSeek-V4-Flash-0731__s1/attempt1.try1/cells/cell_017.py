
import numpy as np
import datetime

# Load data
baseline_dates_str = np.load('baseline_dates.npy', allow_pickle=True)
baseline_dt = [datetime.datetime.strptime(str(s), '%Y-%m-%d') for s in baseline_dates_str]

# Check pool 1 (Jan 1)
print("Pool 1 dates (should include Dec 27-31, 1991):")
for i in range(5):
    print(f"  {baseline_dt[i]}")

# Pool 366 (Dec 31)
# Need to check if pool 366 includes 2003-01-01 to 2003-01-05
pool_366 = []
for i, dt in enumerate(baseline_dt):
    # Check if dt is within ±5 days of any Dec 31 in 1992-2002
    for y in range(1992, 2003):
        D = datetime.datetime(y, 12, 31)
        if abs((dt - D).days) <= 5:
            pool_366.append(i)
            break

print(f"\nPool 366 ({len(pool_366)} dates)")
# Check if 2003 dates are included
for i in pool_366:
    if baseline_dt[i].year >= 2003:
        print(f"  {baseline_dt[i]}")
