import numpy as np
from datetime import datetime, timedelta

# Load all the data needed
target_sst = np.load('/tmp/target_sst.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
sea_indices = np.load('/tmp/sea_indices.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
hot = np.load('/tmp/hot.npy')
in_mhw = np.load('/tmp/in_mhw.npy')

# Let's pick a specific sea cell and verify
# Pick cell 0 (first sea cell)
c = 0
lat_i, lon_j = sea_indices[c]

# Target dates
target_dates = []
d = datetime(2019, 6, 1)
while d <= datetime(2019, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

def day_of_year(date):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[date.month - 1] + date.day

print(f"Cell {c}: lat={lat_i}, lon={lon_j}")
print(f"  Hot days: {hot[c].sum()}")
print(f"  In MHW: {in_mhw[c].sum()}")

# Print hot pattern
hot_pattern = ''.join(['H' if hot[c][t] else '.' for t in range(len(target_dates))])
print(f"  Hot pattern: {hot_pattern}")

# Print MHW pattern
mhw_pattern = ''.join(['M' if in_mhw[c][t] else '.' for t in range(len(target_dates))])
print(f"  MHW pattern: {mhw_pattern}")

# Find runs
h = hot[c]
runs = []
i = 0
while i < len(h):
    if h[i]:
        start = i
        while i < len(h) and h[i]:
            i += 1
        end = i - 1
        runs.append((start, end))
    else:
        i += 1
print(f"  Hot runs: {runs}")

long_runs = [(s, e) for (s, e) in runs if (e - s + 1) >= 5]
print(f"  Long runs (>=5): {long_runs}")

# Show SST and threshold for this cell
for t in range(len(target_dates)):
    doy = day_of_year(target_dates[t])
    thr = threshold_smooth[doy - 1, c]
    sst_val = target_sst[t, lat_i, lon_j]
    is_hot = sst_val >= thr
    in_m = in_mhw[c][t]
    marker = 'M' if in_m else ('.' if not is_hot else 'H')
    print(f"  {target_dates[t].strftime('%Y-%m-%d')}: SST={sst_val:.2f}, Thr={thr:.2f}, Hot={is_hot}, MHW={in_m}")
