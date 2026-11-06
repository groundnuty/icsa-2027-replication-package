
import numpy as np
import xarray as xr
import pandas as pd

# Reload
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))
target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_sst = target.analysed_sst.values.astype(np.float64)
target_dates = pd.to_datetime(target.time.values).date

threshold_smooth = np.load('/work/threshold_smooth.npy')
sea_mask = np.load('/work/sea_mask.npy')

CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_md(month, day):
    return CUM[month-1] + day

def get_doy(d):
    return doy_from_md(d.month, d.day)

target_doy = np.array([get_doy(d) for d in target_dates])
n_time = len(target_dates)

# Compute hot
hot = np.zeros((60, 60, n_time), dtype=bool)
for t in range(n_time):
    doy = target_doy[t]
    hot[:, :, t] = (target_sst[t] >= threshold_smooth[doy-1]) & sea_mask

# Original implementation (merge all runs first)
mhw_mask_orig = np.zeros((60, 60, n_time), dtype=bool)
for i in range(60):
    for j in range(60):
        if not sea_mask[i, j]:
            continue
        cell_hot = hot[i, j, :]
        runs = []
        t = 0
        while t < n_time:
            if cell_hot[t]:
                start = t
                while t < n_time and cell_hot[t]:
                    t += 1
                runs.append((start, t-1))
            else:
                t += 1
        
        if len(runs) <= 1:
            joined_runs = runs
        else:
            joined_runs = [runs[0]]
            for r in runs[1:]:
                prev_end = joined_runs[-1][1]
                gap = r[0] - prev_end - 1
                if gap <= 2:
                    joined_runs[-1] = (joined_runs[-1][0], r[1])
                else:
                    joined_runs.append(r)
        
        for start, end in joined_runs:
            if end - start + 1 >= 5:
                mhw_mask_orig[i, j, start:end+1] = True

# Correct implementation (join only MHWs separated by 1-2 non-hot days)
mhw_mask_corr = np.zeros((60, 60, n_time), dtype=bool)
for i in range(60):
    for j in range(60):
        if not sea_mask[i, j]:
            continue
        cell_hot = hot[i, j, :]
        runs = []
        t = 0
        while t < n_time:
            if cell_hot[t]:
                start = t
                while t < n_time and cell_hot[t]:
                    t += 1
                runs.append((start, t-1))
            else:
                t += 1
        
        # Identify MHW run indices (length >= 5)
        mhw_indices = [k for k, (s, e) in enumerate(runs) if e - s + 1 >= 5]
        
        if not mhw_indices:
            continue
        
        # Merge consecutive MHWs
        events = []
        current = [runs[mhw_indices[0]][0], runs[mhw_indices[0]][1]]
        current_ri = mhw_indices[0]
        
        for ri in mhw_indices[1:]:
            mhw_start, mhw_end = runs[ri]
            
            # Count non-hot days between current and this MHW
            total_days = mhw_start - current[1] - 1
            hot_days_between = 0
            for k in range(current_ri + 1, ri):
                hot_days_between += runs[k][1] - runs[k][0] + 1
            non_hot_days = total_days - hot_days_between
            
            if 1 <= non_hot_days <= 2:
                current[1] = mhw_end
                current_ri = ri
            else:
                events.append(tuple(current))
                current = [mhw_start, mhw_end]
                current_ri = ri
        
        events.append(tuple(current))
        
        for start, end in events:
            mhw_mask_corr[i, j, start:end+1] = True

# Compare
diff = np.sum(mhw_mask_orig != mhw_mask_corr)
print("Differences between original and corrected:", diff)

if diff > 0:
    # Find where they differ
    diff_locations = np.where(mhw_mask_orig != mhw_mask_corr)
    print("Number of differing cells:", len(set(zip(diff_locations[0], diff_locations[1]))))
    for idx in range(min(5, len(diff_locations[0]))):
        i, j, t = diff_locations[0][idx], diff_locations[1][idx], diff_locations[2][idx]
        print(f"  Cell ({i},{j}) day {t}: orig={mhw_mask_orig[i,j,t]}, corr={mhw_mask_corr[i,j,t]}")
