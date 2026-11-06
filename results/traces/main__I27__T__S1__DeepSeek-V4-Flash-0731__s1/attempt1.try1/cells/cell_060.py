
import numpy as np
import pandas as pd
import pickle

# Load pool indices
with open('/tmp/pool_indices.pkl', 'rb') as f:
    pool_indices_by_doy = pickle.load(f)

# Load baseline times
baseline_times = pd.DatetimeIndex(np.load('/tmp/baseline_times.npy').astype('datetime64[ns]'))

# Find all dates used in any pool
all_pool_indices = set()
for doy, indices in pool_indices_by_doy.items():
    all_pool_indices.update(indices)

print(f"Total unique pool indices: {len(all_pool_indices)}")
print(f"Total baseline dates: {len(baseline_times)}")

# Find dates not in any pool
all_indices = set(range(len(baseline_times)))
not_in_pool = all_indices - all_pool_indices
print(f"Dates not in any pool: {len(not_in_pool)}")

if not_in_pool:
    not_in_pool_sorted = sorted(not_in_pool)
    print("Not in pool dates:")
    for i in not_in_pool_sorted:
        print(f"  {baseline_times[i].date()}")
    
    # Find the first and last dates in pools
    used_indices = sorted(all_pool_indices)
    first_used = baseline_times[used_indices[0]].date()
    last_used = baseline_times[used_indices[-1]].date()
    print(f"\nFirst date used in pools: {first_used}")
    print(f"Last date used in pools: {last_used}")
else:
    print("All dates are in at least one pool")
    used_indices = sorted(all_pool_indices)
    first_used = baseline_times[used_indices[0]].date()
    last_used = baseline_times[used_indices[-1]].date()
    print(f"First date used: {first_used}")
    print(f"Last date used: {last_used}")
