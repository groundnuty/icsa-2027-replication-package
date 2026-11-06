
import numpy as np
import pandas as pd

# Load data
time_int = np.load('/tmp/time_sub.npy')
time_sub = time_int.astype('datetime64[s]')

# Check target days
target_start = np.datetime64('2022-06-01')
target_end = np.datetime64('2022-08-31')
target_mask = (time_sub >= target_start) & (time_sub <= target_end)
target_idx = np.where(target_mask)[0]

print(f"Target days: {len(target_idx)}")
print(f"Expected: 92 days (Jun 1 to Aug 31)")

# Check for gaps in the target period
target_dates = pd.to_datetime(time_sub[target_idx])
expected = pd.date_range('2022-06-01', '2022-08-31', freq='D')
print(f"All target dates present: {len(target_dates) == len(expected) and all(target_dates == expected)}")

# Check first and last
print(f"First target date: {target_dates[0]}")
print(f"Last target date: {target_dates[-1]}")

# Also verify no gaps in the full time series
all_dates = pd.to_datetime(time_sub)
diff = np.diff(all_dates.astype('int64') // 86400000000000)  # days
if len(diff) > 0:
    non_daily = np.where(diff != 1)[0]
    if len(non_daily) > 0:
        print(f"Non-daily gaps at: {non_daily[:10]}")
        for i in non_daily[:10]:
            print(f"  {all_dates[i]} to {all_dates[i+1]}")
    else:
        print("Time series is fully daily with no gaps")
else:
    print("Only one time step")
