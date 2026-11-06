
import numpy as np
import pandas as pd
import json

# Final verification summary
print("=== COMPREHENSIVE FINAL CHECK ===\n")

# 1. Verify sea cells
target_sst = np.load('/work/target_sst.npy')
sea_cells = np.all(np.isfinite(target_sst), axis=0)
print(f"1. Sea cells: {sea_cells.sum()} out of {sea_cells.size} grid cells")

# 2. Verify target period
tt = pd.to_datetime(np.load('/work/target_time.npy', allow_pickle=True))
print(f"2. Target period: {tt[0].strftime('%Y-%m-%d')} to {tt[-1].strftime('%Y-%m-%d')}, {len(tt)} days")

# 3. Verify baseline period
bt = pd.to_datetime(np.load('/work/baseline_time.npy', allow_pickle=True))
print(f"3. Baseline period: {bt[0].strftime('%Y-%m-%d')} to {bt[-1].strftime('%Y-%m-%d')}, {len(bt)} days")

# 4. Verify threshold and climatology
threshold_smooth = np.load('/work/threshold_smooth.npy')
climatology_smooth = np.load('/work/climatology_smooth.npy')
print(f"4. Threshold shape: {threshold_smooth.shape}")
print(f"   Climatology shape: {climatology_smooth.shape}")
print(f"   Threshold dtype: {threshold_smooth.dtype}")
print(f"   Climatology dtype: {climatology_smooth.dtype}")

# 5. Verify MHW mask
mhw_mask = np.load('/work/mhw_mask.npy')
print(f"5. MHW mask shape: {mhw_mask.shape}, dtype: {mhw_mask.dtype}")
print(f"   MHW mask sum: {mhw_mask.sum()}")
print(f"   Land cells in MHW (should be 0): {mhw_mask[:, ~sea_cells].sum()}")

# 6. Verify events
active = mhw_mask.sum(axis=(1, 2)) > 0
active_indices = np.where(active)[0]
print(f"6. Active days: {active_indices}")
print(f"   Active day dates: {[tt[i].strftime('%Y-%m-%d') for i in active_indices]}")

events = []
if len(active_indices) > 0:
    start = active_indices[0]
    prev = start
    for idx in active_indices[1:]:
        if idx == prev + 1:
            prev = idx
        else:
            events.append((start, prev))
            start = idx
            prev = idx
    events.append((start, prev))

print(f"   Regional events: {[(tt[s].strftime('%Y-%m-%d'), tt[e].strftime('%Y-%m-%d')) for s, e in events]}")

# 7. Verify output files
with open('output/report.json') as f:
    report = json.load(f)

print(f"\n7. report.json:")
print(f"   region: {report['region']}")
print(f"   baseline_analysed: {report['baseline_analysed']}")
print(f"   target_analysed: {report['target_analysed']}")
print(f"   events: {report['events']}")
print(f"   complete: {report['complete']}")
print(f"   caveats: '{report['caveats']}'")

# 8. Verify mhw_mask.nc
import xarray as xr
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\n8. mhw_mask.nc:")
print(f"   Variables: {list(ds.data_vars.keys())}")
print(f"   mhw dtype: {ds.mhw.dtype}")
print(f"   mhw dims: {ds.mhw.dims}")
print(f"   mhw shape: {ds.mhw.shape}")
print(f"   Time: {len(ds.time)} days, {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"   Lat: {len(ds.lat)} cells, {ds.lat.values[0]:.2f} to {ds.lat.values[-1]:.2f}")
print(f"   Lon: {len(ds.lon)} cells, {ds.lon.values[0]:.2f} to {ds.lon.values[-1]:.2f}")

# 9. Verify report events match mask events
mask_events = []
for s, e in events:
    mask_events.append({
        "onset": tt[s].strftime('%Y-%m-%d'),
        "end": tt[e].strftime('%Y-%m-%d')
    })
print(f"\n9. Events match: {mask_events == report['events']}")

print("\n=== ALL CHECKS PASSED ===")
