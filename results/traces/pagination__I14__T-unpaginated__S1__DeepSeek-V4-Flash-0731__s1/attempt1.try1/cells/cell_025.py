
import numpy as np

target_sst = np.load('target_sst.npy')
sea_mask = np.load('sea_mask.npy')
threshold_smooth = np.load('threshold_smooth.npy')
per_cell_mhw = np.load('per_cell_mhw.npy')

def day_of_year_fixed(y, m, d):
    if m == 1:
        return d
    elif m == 2:
        return 31 + d
    else:
        days_before_month = {3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}
        return days_before_month[m] + d

from datetime import date, timedelta
target_dates = []
d = date(2015, 6, 1)
while d <= date(2015, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)
target_doy = np.array([day_of_year_fixed(d.year, d.month, d.day) for d in target_dates])

# Find cells active on day 30 (July 1)
active_cells_30 = np.argwhere(per_cell_mhw[30])
print(f"Cells in MHW on July 1: {len(active_cells_30)}")
for lat_i, lon_i in active_cells_30[:3]:
    print(f"\nCell ({lat_i}, {lon_i}):")
    hot_series = np.zeros(len(target_dates), dtype=bool)
    for t in range(len(target_dates)):
        sst = target_sst[t, lat_i, lon_i]
        thr = threshold_smooth[target_doy[t]-1, lat_i, lon_i]
        if np.isfinite(sst) and np.isfinite(thr) and sst >= thr:
            hot_series[t] = True
    
    # Show hot days
    print("  Hot days:", end=" ")
    for t in range(len(target_dates)):
        if hot_series[t]:
            print(f"{target_dates[t].isoformat()}", end=" ")
    print()
    
    # Show MHW days
    print("  MHW days:", end=" ")
    for t in range(len(target_dates)):
        if per_cell_mhw[t, lat_i, lon_i]:
            print(f"{target_dates[t].isoformat()}", end=" ")
    print()
