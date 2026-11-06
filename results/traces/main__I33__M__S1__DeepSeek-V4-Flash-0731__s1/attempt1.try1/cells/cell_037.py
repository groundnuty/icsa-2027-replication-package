
import numpy as np
from datetime import datetime, timezone, timedelta

# Load data
target_sst = np.load('output/target_sst.npy')
sea_cells = np.load('output/sea_cells.npy')
threshold_smooth = np.load('output/threshold_smooth.npy')
mhw_mask = np.load('output/mhw_mask.npy')

# Check cell (0,0)
lat, lon = 0, 0
print(f"Cell ({lat},{lon}) - sea cell: {sea_cells[lat, lon]}")

# Check if cell is in an MHW and when
mhw_cell = mhw_mask[:, lat, lon]
hot_days = np.where(mhw_cell > 0)[0]
print(f"MHW days for cell ({lat},{lon}): {hot_days}")

if len(hot_days) > 0:
    # Check SST >= threshold on MHW days
    first_day = int(hot_days[0])
    sst_cell = target_sst[first_day, lat, lon]
    
    # Get day of year for this target day
    target_start = datetime(2014, 6, 1, tzinfo=timezone.utc)
    day_dt = target_start + timedelta(days=first_day)
    starts = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    d_doy = starts[day_dt.month] + day_dt.day
    thr = threshold_smooth[d_doy - 1, lat, lon]
    
    print(f"First MHW day: {first_day} = {day_dt.date()}, doy={d_doy}")
    print(f"SST: {sst_cell:.4f}, Threshold: {thr:.4f}")
    print(f"SST >= Threshold: {sst_cell >= thr}")

# Check the day before the MHW starts
if len(hot_days) > 0:
    prev_day = int(hot_days[0]) - 1
    if prev_day >= 0:
        sst_prev = target_sst[prev_day, lat, lon]
        target_start = datetime(2014, 6, 1, tzinfo=timezone.utc)
        day_dt = target_start + timedelta(days=prev_day)
        d_doy = starts[day_dt.month] + day_dt.day
        thr_prev = threshold_smooth[d_doy - 1, lat, lon]
        print(f"Day before MHW ({day_dt.date()}): SST={sst_prev:.4f}, Thr={thr_prev:.4f}, Hot: {sst_prev >= thr_prev}")

# Check the day after the MHW ends
if len(hot_days) > 0:
    next_day = int(hot_days[-1]) + 1
    if next_day < 92:
        sst_next = target_sst[next_day, lat, lon]
        target_start = datetime(2014, 6, 1, tzinfo=timezone.utc)
        day_dt = target_start + timedelta(days=next_day)
        d_doy = starts[day_dt.month] + day_dt.day
        thr_next = threshold_smooth[d_doy - 1, lat, lon]
        print(f"Day after MHW ({day_dt.date()}): SST={sst_next:.4f}, Thr={thr_next:.4f}, Hot: {sst_next >= thr_next}")

# Check how many cells have MHWs
cells_with_mhw = (mhw_mask.sum(axis=0) > 0)
print(f"\nCells with MHWs: {cells_with_mhw.sum()} / {sea_cells.sum()} sea cells")
print(f"All sea cells have MHWs: {np.all(cells_with_mhw[sea_cells])}")

# Check the active days
active = mhw_mask.sum(axis=(1, 2)) > 0
print(f"\nActive days (out of {len(active)}): {active.sum()}")
first_active = int(np.where(active)[0][0])
last_active = int(np.where(active)[0][-1])
print(f"First active day: {first_active}")
print(f"Last active day: {last_active}")
print(f"All days between are active: {np.all(active[first_active:last_active+1])}")
