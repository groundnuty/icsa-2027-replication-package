
import numpy as np
import xarray as xr
import pandas as pd

# Load saved data
target_data = xr.open_dataset('target_data.nc')
thresholds_smooth = np.load('thresholds_smooth.npy')

target_sst = target_data.analysed_sst.values
target_time = target_data.time.values
n_days, n_lat, n_lon = target_sst.shape

cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def date_to_doy(year, month, day):
    return cum_days[month-1] + day

target_dates = [pd.Timestamp(t).date() for t in target_time.astype('datetime64[D]')]
target_doys = [date_to_doy(d.year, d.month, d.day) for d in target_dates]

# Sea cells
sea_mask = np.all(~np.isnan(target_sst), axis=0)
print("Sea cells:", np.sum(sea_mask))

# Check a specific sea cell - let's find one in the middle of the region
mid_lat = n_lat // 2
mid_lon = n_lon // 2
# Find a sea cell near the middle
found = False
for i in range(mid_lat, n_lat):
    for j in range(mid_lon, n_lon):
        if sea_mask[i, j]:
            print(f"Checking sea cell at ({i},{j})")
            print(f"  lat={target_data.latitude.values[i]}, lon={target_data.longitude.values[j]}")
            
            # Get SST and threshold
            sst_cell = target_sst[:, i, j]
            thresh_cell = np.array([thresholds_smooth[doy, i, j] for doy in target_doys])
            
            # Check hot days
            hot_cell = sst_cell >= thresh_cell
            print(f"  Hot days: {np.sum(hot_cell)}")
            
            # Find runs
            runs = []
            in_run = False
            run_start = 0
            for d in range(n_days):
                if hot_cell[d]:
                    if not in_run:
                        run_start = d
                        in_run = True
                else:
                    if in_run:
                        runs.append((run_start, d-1))
                        in_run = False
            if in_run:
                runs.append((run_start, n_days-1))
            
            print(f"  Runs: {runs}")
            
            # Long runs
            long_runs = [r for r in runs if r[1]-r[0]+1 >= 5]
            print(f"  Long runs (>=5): {long_runs}")
            
            # Join
            if len(long_runs) > 0:
                joined = [list(long_runs[0])]
                for k in range(1, len(long_runs)):
                    gap = long_runs[k][0] - joined[-1][1] - 1
                    print(f"    Gap between runs: {gap}")
                    if gap <= 2:
                        joined[-1][1] = long_runs[k][1]
                    else:
                        joined.append(list(long_runs[k]))
                print(f"  Joined runs: {joined}")
            
            # Print SST, threshold, hot for first 20 days
            print("\n  First 20 days (SST, threshold, hot):")
            for d in range(min(20, n_days)):
                print(f"    Day {d} ({target_dates[d]}): SST={sst_cell[d]:.4f}, Thresh={thresh_cell[d]:.4f}, Hot={hot_cell[d]}")
            
            found = True
            break
    if found:
        break
