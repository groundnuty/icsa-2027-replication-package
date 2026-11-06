
import numpy as np
import pandas as pd
import time

# Load data
baseline_sst = np.load('/work/baseline_sst.npy')  # (4028, 60, 60) float64
baseline_time = np.load('/work/baseline_time.npy', allow_pickle=True)
target_sst = np.load('/work/target_sst.npy')  # (92, 60, 60) float64
target_time = np.load('/work/target_time.npy', allow_pickle=True)

bt = pd.to_datetime(baseline_time)
tt = pd.to_datetime(target_time)

n_baseline, n_lat, n_lon = baseline_sst.shape
n_target = target_sst.shape[0]

print(f"baseline: {n_baseline} days, {n_lat} lat, {n_lon} lon")
print(f"target: {n_target} days")

# Step 1: Identify sea cells (finite SST on all target days)
# target_sst shape: (92, 60, 60)
sea_cells = np.all(np.isfinite(target_sst), axis=0)  # (60, 60) boolean
print(f"Sea cells: {sea_cells.sum()} out of {n_lat*n_lon}")

# Step 2: Compute threshold and climatology per sea cell and doy
# Define doy mapping
cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def doy_from_md(m, d):
    return cum[m-1] + d

# Compute doy for each baseline date
baseline_doy = np.array([doy_from_md(t.month, t.day) for t in bt])

# For each doy d (1..366, d != 60), compute the pool mask
print("Computing pools...")
start = time.time()

# Find baseline dates within [1992-01-01, 2002-12-31]
in_baseline_range = (bt >= pd.Timestamp('1992-01-01')) & (bt <= pd.Timestamp('2002-12-31'))
print(f"Baseline dates in 1992-2002 range: {in_baseline_range.sum()}")

# For each doy, find which baseline time indices are in the pool
pools = {}  # doy -> boolean mask over baseline time

for d in range(1, 367):
    if d == 60:
        continue
    # Find baseline dates with doy d in [1992-01-01, 2002-12-31]
    t0_idx = np.where((baseline_doy == d) & in_baseline_range)[0]
    mask_d = np.zeros(n_baseline, dtype=bool)
    for idx in t0_idx:
        t0 = bt[idx]
        w_start = t0 - pd.Timedelta(days=5)
        w_end = t0 + pd.Timedelta(days=5)
        mask_d |= (bt >= w_start) & (bt <= w_end)
    pools[d] = mask_d
    if d % 50 == 0:
        print(f"  doy {d}: pool size = {mask_d.sum()}")

print(f"Pool computation took {time.time()-start:.2f}s")

# Save pools for reuse
np.save('/work/pools_keys.npy', np.array(sorted(pools.keys())))
# Save each pool mask
for d in sorted(pools.keys()):
    np.save(f'/work/pool_{d}.npy', pools[d])
print("Saved pools")
