import numpy as np
from datetime import date, timedelta
import pickle

# Reload all intermediate data
target_sst = np.load('/tmp/work/target_sst.npy')
with open('/tmp/work/target_dates.pkl', 'rb') as f:
    target_dates = pickle.load(f)
sea_cells = np.load('/tmp/work/sea_cells.npy')
threshold_smooth = np.load('/tmp/work/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/work/climatology_smooth.npy')
per_cell_mhw = np.load('/tmp/work/per_cell_mhw.npy')
active = np.load('/tmp/work/active_days.npy')
with open('/tmp/work/events.pkl', 'rb') as f:
    events = pickle.load(f)

print("All intermediate data loaded successfully.")
print(f"Target SST: {target_sst.shape}")
print(f"Sea cells: {sea_cells.sum()}")
print(f"Per-cell MHW days: {per_cell_mhw.sum()}")
print(f"Active days: {active.sum()}")
print(f"Events: {events}")

# Verify the events
for s, e in events:
    print(f"  Event: {target_dates[s]} to {target_dates[e]}, length={e-s+1} days")

# Verify target dates
print(f"\nTarget dates: {len(target_dates)} from {target_dates[0]} to {target_dates[-1]}")
