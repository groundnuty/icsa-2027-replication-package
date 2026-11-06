
import numpy as np
from datetime import date, timedelta

# Load data
target_sst = np.load('/tmp/target_sst.npy')
thr_smooth = np.load('/tmp/thr_smooth.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')

# Day-of-year mapping
month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
cum_days = [0]
for md in month_days[:-1]:
    cum_days.append(cum_days[-1] + md)

def date_to_doy(d):
    return cum_days[d.month - 1] + d.day

target_start = date(2022, 6, 1)
target_end = date(2022, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

# Pick a specific sea cell and verify its MHW detection
sea_indices = np.where(sea_cells)
si, sj = sea_indices[0][0], sea_indices[1][0]

# Compute hot days for this cell
hot = np.zeros(len(target_dates), dtype=bool)
for t in range(len(target_dates)):
    doy = date_to_doy(target_dates[t])
    hot[t] = target_sst[t, si, sj] >= thr_smooth[doy-1, si, sj]

# Manually find runs and join
runs = []
in_run = False
run_start = 0
for t in range(len(target_dates)):
    if hot[t]:
        if not in_run:
            run_start = t
            in_run = True
    else:
        if in_run:
            runs.append((run_start, t-1))
            in_run = False
if in_run:
    runs.append((run_start, len(target_dates)-1))

# Filter runs >= 5
runs5 = [(s, e) for s, e in runs if e - s + 1 >= 5]
print(f"Cell ({si},{sj}): hot runs >= 5 days:")
for s, e in runs5:
    print(f"  {target_dates[s].isoformat()} to {target_dates[e].isoformat()} ({e-s+1} days)")

# Join runs with gaps of 1-2
joined = [runs5[0]] if runs5 else []
for r in runs5[1:]:
    ps, pe = joined[-1]
    cs, ce = r
    gap = cs - pe - 1
    if 1 <= gap <= 2:
        joined[-1] = (ps, ce)
    else:
        joined.append(r)

print(f"\nJoined MHW runs:")
for s, e in joined:
    print(f"  {target_dates[s].isoformat()} to {target_dates[e].isoformat()} ({e-s+1} days)")

# Verify against mhw_mask
print(f"\nMHW mask for this cell:")
for t in range(len(target_dates)):
    mask_val = mhw_mask[t, si, sj]
    in_joined = any(s <= t <= e for s, e in joined)
    if mask_val != in_joined:
        print(f"  MISMATCH at {target_dates[t]}: mask={mask_val}, computed={in_joined}")

print("Verification complete")
