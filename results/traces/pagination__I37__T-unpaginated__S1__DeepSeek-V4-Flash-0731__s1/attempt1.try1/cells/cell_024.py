
import numpy as np
import datetime

# Load data
target_sst = np.load('work/target_sst.npy')
sea_mask = np.load('work/sea_mask.npy')
threshold_smooth = np.load('work/threshold_smooth.npy')
climatology_smooth = np.load('work/climatology_smooth.npy')

# Day of year mapping
def doy_from_date(date):
    month_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days[date.month-1] + date.day

# Target dates
target_start = datetime.date(2012, 6, 1)
target_end = datetime.date(2012, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += datetime.timedelta(days=1)

target_doy = np.array([doy_from_date(date) for date in target_dates])

n_target = len(target_dates)
n_lat, n_lon = 60, 60

threshold_3d = threshold_smooth.reshape(366, n_lat, n_lon)
climatology_3d = climatology_smooth.reshape(366, n_lat, n_lon)

# Look at some sea cells
sea_cells = np.argwhere(sea_mask)
print(f"Number of sea cells: {len(sea_cells)}")

# Check a few sea cells
for idx in sea_cells[:5]:
    i, j = idx
    print(f"\nCell ({i},{j}):")
    # Show SST, threshold, climatology for first few target days
    for t in range(0, 10):
        date = target_dates[t]
        doy = target_doy[t]
        sst = target_sst[t, i, j]
        thr = threshold_3d[doy-1, i, j]
        clim = climatology_3d[doy-1, i, j]
        hot_flag = sst >= thr
        print(f"  {date} doy={doy}: sst={sst:.2f}, thr={thr:.2f}, clim={clim:.2f}, hot={hot_flag}")

# Check some more cells later in the period
print("\n\nMore cells, later days:")
for idx in sea_cells[100:103]:
    i, j = idx
    print(f"\nCell ({i},{j}):")
    for t in range(60, 75):
        date = target_dates[t]
        doy = target_doy[t]
        sst = target_sst[t, i, j]
        thr = threshold_3d[doy-1, i, j]
        clim = climatology_3d[doy-1, i, j]
        hot_flag = sst >= thr
        print(f"  {date} doy={doy}: sst={sst:.2f}, thr={thr:.2f}, clim={clim:.2f}, hot={hot_flag}")
