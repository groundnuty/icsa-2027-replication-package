
import numpy as np
import pandas as pd

thr_smooth = np.load('/work/thr_smooth.npy')
target_arr = np.load('/work/target_arr.npy')
target_time = np.load('/work/target_time.npy').astype('datetime64[D]')
mhw_mask = np.load('/work/mhw_mask.npy')

def date_to_doy(dt):
    d = pd.Timestamp(dt)
    month, day = d.month, d.day
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month-1] + day

target_doy = np.array([date_to_doy(t) for t in target_time])
target_doy_idx = target_doy - 1

# Pick a sea cell and check
sea_mask = np.all(np.isfinite(target_arr), axis=0)
sea_cells = np.argwhere(sea_mask)
print("First few sea cells:", sea_cells[:5])

# Check cell (i, j) = first sea cell
i, j = sea_cells[0]
print(f"\nCell ({i}, {j})")
print("SST:", target_arr[:, i, j])
thr_cell = thr_smooth[target_doy_idx, i, j]
print("Threshold:", thr_cell)
print("Hot:", target_arr[:, i, j] >= thr_cell)
print("MHW:", mhw_mask[:, i, j])

# Verify against manual calculation for this cell
hot = target_arr[:, i, j] >= thr_cell

# Find runs of >= 5 consecutive hot days
runs = []
in_run = False
run_start = 0
for d in range(len(hot)):
    if hot[d] and not in_run:
        in_run = True
        run_start = d
    elif not hot[d] and in_run:
        in_run = False
        runs.append((run_start, d-1))
if in_run:
    runs.append((run_start, len(hot)-1))

print("\nAll runs (including short):", runs)
long_runs = [r for r in runs if r[1]-r[0]+1 >= 5]
print("Long runs (>=5):", long_runs)

# Join
if long_runs:
    joined = []
    current = long_runs[0]
    for nr in long_runs[1:]:
        gap = nr[0] - current[1] - 1
        if 1 <= gap <= 2:
            current = (current[0], nr[1])
        else:
            joined.append(current)
            current = nr
    joined.append(current)
    print("Joined runs:", joined)
    
    # Check against mhw_mask
    manual_mhw = np.zeros(len(hot), dtype=np.uint8)
    for s, e in joined:
        manual_mhw[s:e+1] = 1
    print("Manual MHW matches computed:", np.array_equal(manual_mhw, mhw_mask[:, i, j]))
