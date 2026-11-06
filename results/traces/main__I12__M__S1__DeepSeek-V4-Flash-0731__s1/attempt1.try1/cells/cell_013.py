
import numpy as np
from datetime import date, timedelta

# Load baseline data
baseline_data = np.load('/tmp/baseline_data.npy')
n_dates, n_lat, n_lon = baseline_data.shape
print(f"Baseline data: {baseline_data.shape}")

# Baseline dates
base_start = date(1991, 12, 27)
base_end = date(2003, 1, 5)
base_dates = []
d = base_start
while d <= base_end:
    base_dates.append(d)
    d += timedelta(days=1)

# Create a map from date to index
date_to_idx = {d: i for i, d in enumerate(base_dates)}

# Day of year function
def day_of_year(d):
    month = d.month
    day = d.day
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month]) + day
    if month > 2:
        doy += 1
    return doy

# Build baseline_by_doy
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)
baseline_by_doy = {}
d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d)
    if doy not in baseline_by_doy:
        baseline_by_doy[doy] = []
    baseline_by_doy[doy].append(d)
    d += timedelta(days=1)

# For each day of year d (except 60), build pool indices
pool_indices = {}  # doy -> list of indices into baseline_data

for doy in range(1, 367):
    if doy == 60:
        continue
    idx_list = []
    for bd in baseline_by_doy.get(doy, []):
        for i in range(-5, 6):
            cd = bd + timedelta(days=i)
            idx_list.append(date_to_idx[cd])
    pool_indices[doy] = np.array(idx_list, dtype=np.int32)

print("Pool sizes for select days:")
for doy in [1, 59, 61, 152, 244, 366]:
    print(f"  Day {doy}: {len(pool_indices[doy])} entries")
