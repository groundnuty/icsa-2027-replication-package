
import numpy as np
from datetime import date, timedelta
import json

intermediate_dir = 'intermediate'

# Load metadata
with open(f'{intermediate_dir}/metadata.json') as f:
    meta = json.load(f)

target_dates = [date.fromisoformat(d) for d in meta['target_dates']]
region_lats = np.load(f'{intermediate_dir}/region_lats.npy')
region_lons = np.load(f'{intermediate_dir}/region_lons.npy')

# Load data
threshold_smooth = np.load(f'{intermediate_dir}/threshold_smooth.npy')
climatology_smooth = np.load(f'{intermediate_dir}/climatology_smooth.npy')
sea_cells = np.load(f'{intermediate_dir}/sea_cells.npy')
target_sst = np.load(f'{intermediate_dir}/target_sst.npy')

# Day of year mapping
def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:d.month]) + d.day

# Find a sea cell that's active during the regional event
# Let's check which cells are active on day 44 (July 14) 
# day index 43 = July 14 (day 43 in 0-indexed: June 1=0, June 30=29, July 1=30, July 14=43)

# Wait, let me compute: June 1 = 0, June 30 = 29, July 1 = 30, July 14 = 43
# So day index 43 in target_dates corresponds to July 14

# Let's find which cells are active during the event period
# Event: day 43 to day 68 (July 14 to Aug 8)
# Active day indices 43-68 in 0-indexed

# Let me just check a few cells
sea_indices = np.argwhere(sea_cells)
print(f"Total sea cells: {len(sea_indices)}")

# Check a cell that should be in an MHW
# Let me check cell at some location and compute its MHW status
for idx in range(min(5, len(sea_indices))):
    la, lo = sea_indices[idx]
    print(f"\nCell ({la}, {lo}), lat={region_lats[la]:.2f}, lon={region_lons[lo]:.2f}")
    # Check SST and threshold on some days
    for day_idx in [43, 44, 45, 50, 60, 68, 69]:
        doy = day_of_year(target_dates[day_idx])
        sst_val = target_sst[day_idx, la, lo]
        th_val = threshold_smooth[doy - 1, la, lo]
        hot_val = sst_val >= th_val if not np.isnan(sst_val) else False
        print(f"  Day {day_idx} ({target_dates[day_idx]}): SST={sst_val:.2f}, Threshold={th_val:.2f}, Hot={hot_val}")
