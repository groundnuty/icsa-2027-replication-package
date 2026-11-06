
import numpy as np
import xarray as xr
import pandas as pd

# Load the data
target_data = xr.open_dataset('target_data.nc')
thresholds_smooth = np.load('thresholds_smooth.npy')
target_sst = target_data.analysed_sst.values
n_days, n_lat, n_lon = target_sst.shape

cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def date_to_doy(year, month, day):
    return cum_days[month-1] + day

target_time = target_data.time.values
target_dates = [pd.Timestamp(t).date() for t in target_time.astype('datetime64[D]')]
target_doys = [date_to_doy(d.year, d.month, d.day) for d in target_dates]

sea_mask = np.all(~np.isnan(target_sst), axis=0)

# Verify that all sea cells have at least one MHW event or none
# Check a cell at a different location
# Let's find a cell with MHW activity starting on day 48 (July 19)
# which was the first day with any active cells

# Load the output mask
ds = xr.open_dataset('output/mhw_mask.nc')
mhw_from_file = ds.mhw.values

# Check the first active day (day 48)
print("Cells with MHW on day 48 (July 19):")
count = 0
for i in range(n_lat):
    for j in range(n_lon):
        if mhw_from_file[48, i, j] == 1:
            print(f"  Cell ({i},{j}): lat={target_data.latitude.values[i]}, lon={target_data.longitude.values[j]}")
            count += 1
            if count >= 5:
                break
    if count >= 5:
        break

# Check the last active day (day 80, Aug 20)
print(f"\nCells with MHW on day 80 (Aug 20):")
count = 0
for i in range(n_lat):
    for j in range(n_lon):
        if mhw_from_file[80, i, j] == 1:
            print(f"  Cell ({i},{j}): lat={target_data.latitude.values[i]}, lon={target_data.longitude.values[j]}")
            count += 1
            if count >= 5:
                break
    if count >= 5:
        break

# Check if any sea cell has 0 MHW activity
no_mhw = 0
for i in range(n_lat):
    for j in range(n_lon):
        if sea_mask[i, j] and np.sum(mhw_from_file[:, i, j]) == 0:
            no_mhw += 1
            if no_mhw <= 3:
                print(f"\nSea cell ({i},{j}) has no MHW activity")
print(f"Sea cells with no MHW activity: {no_mhw}")

# Check cells that have MHWs starting on the first active day (day 48)
day48_cells = np.sum(mhw_from_file[48, :, :])
print(f"\nTotal cells in MHW on day 48: {day48_cells}")

# Check some statistics about MHW durations per cell
durations = []
for i in range(n_lat):
    for j in range(n_lon):
        if sea_mask[i, j]:
            cell_mhw = mhw_from_file[:, i, j]
            if np.sum(cell_mhw) > 0:
                # Find MHW periods
                runs = []
                in_run = False
                for d in range(n_days):
                    if cell_mhw[d]:
                        if not in_run:
                            run_start = d
                            in_run = True
                    else:
                        if in_run:
                            runs.append(d - run_start)
                            in_run = False
                if in_run:
                    runs.append(n_days - run_start)
                for r in runs:
                    durations.append(r)

print(f"\nMHW durations across all sea cells:")
print(f"  Number of per-cell MHWs: {len(durations)}")
print(f"  Min duration: {min(durations)}")
print(f"  Max duration: {max(durations)}")
print(f"  Mean duration: {np.mean(durations):.2f}")
print(f"  Median duration: {np.median(durations):.1f}")
