
import numpy as np
import pandas as pd

# Load baseline time and pool masks
baseline_time = np.load('/work/baseline_time.npy', allow_pickle=True)
bt = pd.to_datetime(baseline_time)
n_baseline = len(bt)

# Load all pool masks
pool_doys = np.load('/work/pools_keys.npy')
all_used = np.zeros(n_baseline, dtype=bool)
for d in pool_doys:
    pool = np.load(f'/work/pool_{int(d)}.npy')
    all_used |= pool

print(f"Baseline days used in at least one pool: {all_used.sum()} out of {n_baseline}")
print(f"Unused days: {np.sum(~all_used)}")

# Check which days are NOT used
unused_dates = bt[~all_used]
if len(unused_dates) > 0:
    print(f"Unused dates: {[d.strftime('%Y-%m-%d') for d in unused_dates]}")
else:
    print("All baseline days are used in at least one pool")

# Verify first and last used days
used_dates = bt[all_used]
print(f"First used day: {used_dates[0].strftime('%Y-%m-%d')}")
print(f"Last used day: {used_dates[-1].strftime('%Y-%m-%d')}")
