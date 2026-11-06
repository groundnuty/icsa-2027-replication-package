
import numpy as np
from datetime import date, timedelta

# Let's verify the computation for a specific sea cell
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

target_dates = []
d = date(2015, 6, 1)
while d <= date(2015, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)
target_doy = np.array([day_of_year_fixed(d.year, d.month, d.day) for d in target_dates])

# Look at first few sea cells
sea_cells = np.argwhere(sea_mask)
for ci in range(min(3, len(sea_cells))):
    lat_i, lon_i = sea_cells[ci]
    print(f"\nCell ({lat_i}, {lon_i}):")
    print("  Date        SST       Threshold  Hot   MHW")
    for t in range(len(target_dates)):
        sst = target_sst[t, lat_i, lon_i]
        thr = threshold_smooth[target_doy[t]-1, lat_i, lon_i]
        is_hot = sst >= thr if np.isfinite(sst) and np.isfinite(thr) else False
        in_mhw = per_cell_mhw[t, lat_i, lon_i]
        if is_hot or in_mhw:
            print(f"  {target_dates[t].isoformat()}  {sst:10.4f}  {thr:10.4f}  {is_hot}  {in_mhw}")
