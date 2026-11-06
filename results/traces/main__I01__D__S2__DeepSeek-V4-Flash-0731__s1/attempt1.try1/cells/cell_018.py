
# Verify the MHW mask is consistent with the hot days and MHW detection logic
import numpy as np
import xarray as xr

ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds_out.mhw.values

# Check that each cell's MHW pattern is consistent:
# If a cell is in an MHW on a day, the run must be at least 5 consecutive days
# and gaps of 1-2 days are joined

# For each sea cell, check the MHW mask
# A cell's mhw pattern should consist of runs where consecutive 1s (with possible 1-2 day 0 gaps) form runs of length >= 5

# Let me check a specific cell that has MHWs
n_tgt = mhw.shape[0]
for li in range(mhw.shape[1]):
    for lo in range(mhw.shape[2]):
        pattern = mhw[:, li, lo]
        if pattern.sum() > 0:
            # Find runs of 1s
            runs = []
            i = 0
            while i < n_tgt:
                if pattern[i] == 1:
                    start = i
                    while i < n_tgt and pattern[i] == 1:
                        i += 1
                    end = i - 1
                    runs.append((start, end))
                else:
                    i += 1
            
            # Check gaps between runs (should be at least 3 non-hot days for separate MHWs)
            for j in range(len(runs)-1):
                gap = runs[j+1][0] - runs[j][1] - 1
                if gap < 3:
                    print(f"Cell ({li},{lo}): runs {runs[j]} and {runs[j+1]} have gap {gap} < 3")
            
            # Check each run is at least 5 days
            for s, e in runs:
                if e - s + 1 < 5:
                    print(f"Cell ({li},{lo}): run ({s},{e}) has length {e-s+1} < 5")
            
            break
    else:
        continue
    break

print("MHW mask consistency check done")

# Also verify that if a day is in a cell's MHW, that day is hot
# (i.e., SST >= threshold). This is implicitly true since we set mhw based on hot days.
# But let's verify a specific cell
# Load the original data and check
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat_sel = ds.latitude.values
lon_sel = ds.longitude.values
lat_idx = np.where((lat_sel >= 54.13) & (lat_sel <= 55.33))[0]
lon_idx = np.where((lon_sel >= 14.67) & (lon_sel <= 15.87))[0]
tgt_start = np.datetime64('2008-06-01')
tgt_end = np.datetime64('2008-08-31')
t_idx_tgt = np.where((ds.time.values >= tgt_start) & (ds.time.values <= tgt_end))[0]
tgt_sst = ds.analysed_sst.isel(time=t_idx_tgt, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

# Find a cell with MHW on day 0
cells_with_mhw_day0 = np.where(mhw[0] == 1)
print(f"\nCells with MHW on day 0: {len(cells_with_mhw_day0[0])}")
if len(cells_with_mhw_day0[0]) > 0:
    li, lo = cells_with_mhw_day0[0][0], cells_with_mhw_day0[1][0]
    print(f"Example cell: lat={lat_sel[lat_idx[li]]}, lon={lon_sel[lon_idx[lo]]}")
    print(f"SST on day 0: {tgt_sst[0, li, lo]}")
    print(f"MHW mask on day 0: {mhw[0, li, lo]}")
    
    # Check the full MHW pattern for this cell
    pattern = mhw[:, li, lo]
    print(f"Full pattern: {pattern}")
