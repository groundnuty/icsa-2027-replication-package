
import numpy as np
import xarray as xr

target_data = xr.open_dataset('target_data.nc')
target_sst = target_data.analysed_sst.values
n_days, n_lat, n_lon = target_sst.shape

sea_mask = np.all(~np.isnan(target_sst), axis=0)

ds = xr.open_dataset('output/mhw_mask.nc')
mhw_from_file = ds.mhw.values

# Count per-cell MHWs for each cell
multi_mhw = 0
for i in range(n_lat):
    for j in range(n_lon):
        if sea_mask[i, j]:
            cell_mhw = mhw_from_file[:, i, j]
            runs = []
            in_run = False
            for d in range(n_days):
                if cell_mhw[d]:
                    if not in_run:
                        run_start = d
                        in_run = True
                else:
                    if in_run:
                        runs.append((run_start, d-1))
                        in_run = False
            if in_run:
                runs.append((run_start, n_days-1))
            if len(runs) > 1:
                multi_mhw += 1
                if multi_mhw <= 5:
                    print(f"Cell ({i},{j}) has {len(runs)} MHWs: {runs}")
                    print(f"  Dates: {[target_data.time.values[s].astype('datetime64[D]') for s, e in runs]}")

print(f"\nSea cells with multiple per-cell MHWs: {multi_mhw}")
print(f"Sea cells with exactly 1 per-cell MHW: {3290 - multi_mhw}")

# Check total per-cell MHWs
total_mhws = 0
for i in range(n_lat):
    for j in range(n_lon):
        if sea_mask[i, j]:
            cell_mhw = mhw_from_file[:, i, j]
            runs = []
            in_run = False
            for d in range(n_days):
                if cell_mhw[d]:
                    if not in_run:
                        run_start = d
                        in_run = True
                else:
                    if in_run:
                        runs.append((run_start, d-1))
                        in_run = False
            if in_run:
                runs.append((run_start, n_days-1))
            total_mhws += len(runs)

print(f"Total per-cell MHWs: {total_mhws}")
