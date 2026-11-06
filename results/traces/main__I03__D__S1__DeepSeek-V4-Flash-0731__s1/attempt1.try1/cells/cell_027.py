
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

print(f"mhw_mask shape: {mhw_mask.shape}")
print(f"target_dates: {len(target_dates)}")
print(f"events: {events}")

# Verify mask has correct dimensions
n_target = len(target_dates)
assert mhw_mask.shape == (n_target, len(lats), len(lons)), f"Unexpected shape: {mhw_mask.shape}"

# Check that sea cells outside the region have 0 (they do, since we initialize to 0)
# Check that land cells have 0
non_sea = ~sea_cells
if np.any(mhw_mask[:, non_sea] != 0):
    print("WARNING: Land cells have non-zero mhw values!")
else:
    print("OK: Land cells have 0 mhw values")

# Check that sea cells inside MHW have 1
print(f"Sea cells inside MHW on any day: {np.any(mhw_mask[sea_cells] > 0)}")
print(f"Total mhw=1 entries: {np.sum(mhw_mask)}")

# Verify events
print(f"\nRegional events:")
for s, e in events:
    print(f"  {target_dates[s].date()} to {target_dates[e].date()}")
