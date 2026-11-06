
import numpy as np
import pickle
import json
import xarray as xr
import datetime as dt
import os

# ============================================================
# Reload state and verify
# ============================================================
sea_cells = np.load('/work/sea_cells.npy')
target_sst = np.load('/work/target_sst.npy')
threshold_smoothed = np.load('/work/threshold_smoothed.npy')
climatology_smoothed = np.load('/work/climatology_smoothed.npy')
mhw_mask = np.load('/work/mhw_mask.npy')

with open('/work/target_dates.pkl', 'rb') as f:
    target_dates = pickle.load(f)
with open('/work/events.pkl', 'rb') as f:
    events = pickle.load(f)
lats = np.load('/work/lats.npy')
lons = np.load('/work/lons.npy')

n_target = len(target_dates)
print(f"mhw_mask shape: {mhw_mask.shape}")
print(f"target_dates: {n_target}")
print(f"events: {events}")
print(f"lats: {lats[0]} to {lats[-1]}, count: {len(lats)}")
print(f"lons: {lons[0]} to {lons[-1]}, count: {len(lons)}")

# Verify: non-sea cells should have 0
non_sea = ~sea_cells
if np.any(mhw_mask[:, non_sea] != 0):
    print("WARNING: Land cells have non-zero mhw values!")
else:
    print("OK: Land cells have 0 mhw values")

# Verify: sea cells can have 0 or 1
print(f"Total mhw=1 entries: {np.sum(mhw_mask)}")
print(f"Max value: {np.max(mhw_mask)}")

# Verify events correspond to active days
active = np.any(mhw_mask > 0, axis=(1, 2))
for s, e in events:
    assert all(active[s:e+1]), f"Event {s}-{e} has inactive day"
    if s > 0:
        assert not active[s-1], f"Event {s}-{e} should start at {s}, but day {s-1} is active"
    if e < n_target - 1:
        assert not active[e+1], f"Event {s}-{e} should end at {e}, but day {e+1} is active"
print("Events verification passed")

# Print active days for reference
print("\nActive days:")
for t in range(n_target):
    if active[t]:
        print(f"  {target_dates[t].date()}: active (cells: {np.sum(mhw_mask[t] > 0)})")
