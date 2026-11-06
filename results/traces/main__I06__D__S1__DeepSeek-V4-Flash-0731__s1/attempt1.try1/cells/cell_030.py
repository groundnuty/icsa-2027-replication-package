
import numpy as np
import datetime
import pandas as pd

# Load all data
target_sst = np.load('/work/target_sst.npy')
target_time_idx = np.load('/work/target_time_idx.npy')
thresholds_smooth = np.load('/work/thresholds_smooth.npy')
climatologies_smooth = np.load('/work/climatologies_smooth.npy')

# Check if any sea cell has NaN in smoothed thresholds
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time = ds.time.values
target_dates = time[target_time_idx]
target_dates_list = [pd.Timestamp(t).to_pydatetime().date() for t in target_dates]

# Sea cells
sea_cells = ~np.isnan(target_sst).any(axis=0)
print(f"Sea cells: {sea_cells.sum()}")

# Check NaN in smoothed thresholds for sea cells
for i in range(60):
    for j in range(60):
        if sea_cells[i, j]:
            if np.isnan(thresholds_smooth[:, i, j]).any():
                print(f"WARNING: Sea cell ({i},{j}) has NaN in smoothed thresholds!")
                break
    else:
        continue
    break
else:
    print("No NaN in smoothed thresholds for sea cells")

# Verify threshold computation for one cell
# Take cell (30, 30) - check if it's a sea cell
print(f"\nCell (30,30) is sea: {sea_cells[30, 30]}")
if sea_cells[30, 30]:
    # Verify day 153 threshold
    baseline_sst = np.load('/work/baseline_sst.npy')
    baseline_time_idx = np.load('/work/baseline_time_idx.npy')
    baseline_dates_arr = time[baseline_time_idx]
    baseline_dates_list = [pd.Timestamp(t).to_pydatetime().date() for t in baseline_dates_arr]
    
    def doy_from_date(date):
        m = date.month; d = date.day
        if m == 1: return d
        elif m == 2: return 31 + d
        elif m == 3: return 60 + d
        elif m == 4: return 91 + d
        elif m == 5: return 121 + d
        elif m == 6: return 152 + d
        elif m == 7: return 182 + d
        elif m == 8: return 213 + d
        elif m == 9: return 244 + d
        elif m == 10: return 274 + d
        elif m == 11: return 305 + d
        elif m == 12: return 335 + d
    
    date_to_idx = {}
    for i2, d in enumerate(baseline_dates_list):
        date_to_idx[d] = i2
    
    core_dates = [d for d in baseline_dates_list if datetime.date(1992,1,1) <= d <= datetime.date(2002,12,31)]
    core_doy = {d: doy_from_date(d) for d in core_dates}
    
    # Build pool for day 153
    matching = [d for d, dd in core_doy.items() if dd == 153]
    pool_dates = set()
    for t0 in matching:
        for delta in range(-5, 6):
            t = t0 + datetime.timedelta(days=delta)
            if t in date_to_idx:
                pool_dates.add(t)
    pool_indices = [date_to_idx[d] for d in sorted(pool_dates)]
    
    vals = baseline_sst[pool_indices, 30, 30].astype(np.float64)
    valid = ~np.isnan(vals)
    v = vals[valid]
    
    manual_threshold = np.quantile(v, 0.9, method='hazen')
    manual_clim = np.mean(v)
    
    print(f"Day 153 manual threshold: {manual_threshold:.6f}")
    print(f"Day 153 manual climatology: {manual_clim:.6f}")
    
    # Compare with raw (unsmoothed) computed values
    # Need to recompute from the raw saved arrays
    # But let me just check the smoothed values
    print(f"Day 153 smoothed threshold: {thresholds_smooth[152, 30, 30]:.6f}")
    print(f"Day 153 smoothed climatology: {climatologies_smooth[152, 30, 30]:.6f}")
    
    # The smoothed values should differ from raw values due to smoothing
    # Let me also compute the raw values for comparison
    # Actually I can reload the raw values
    thresholds_raw = np.load('/work/thresholds_raw.npy')
    climatologies_raw = np.load('/work/climatologies_raw.npy')
    print(f"Day 153 raw threshold: {thresholds_raw[152, 30, 30]:.6f}")
    print(f"Day 153 raw climatology: {climatologies_raw[152, 30, 30]:.6f}")
    
    print(f"\nManual threshold matches raw: {abs(manual_threshold - thresholds_raw[152,30,30]) < 1e-10}")
    print(f"Manual clim matches raw: {abs(manual_clim - climatologies_raw[152,30,30]) < 1e-10}")
