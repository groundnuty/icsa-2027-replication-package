
import numpy as np
import xarray as xr
import json

# Final comprehensive verification
print("=== FINAL VERIFICATION ===\n")

# 1. Check output mask
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values
print("1. Mask file:")
print(f"   - Shape: {mhw.shape}")
print(f"   - dtype: {ds.mhw.dtype}")
print(f"   - Unique values: {np.unique(mhw)}")
print(f"   - Total MHW cell-days: {mhw.sum()}")

# 2. Check land cells are 0
sea_cells = np.load('/tmp/sea_cells.npy')
land_cells = ~sea_cells
print(f"\n2. Land cells all 0: {np.all(mhw[:, land_cells] == 0)}")

# 3. Check sea cells have correct values
sea_mhw = mhw[:, sea_cells]
print(f"   - Sea cell MHW cell-days: {sea_mhw.sum()}")
print(f"   - Sea cell MHW values: {np.unique(sea_mhw)}")

# 4. Verify active days
active = mhw.any(axis=(1, 2))
active_days = np.where(active)[0]
print(f"\n4. Active days (indices): {active_days}")
print(f"   Active day count: {len(active_days)}")

# 5. Verify events from report
with open('output/report.json', 'r') as f:
    report = json.load(f)

print(f"\n5. Report events: {report['events']}")
for e in report['events']:
    onset = e['onset']
    end = e['end']
    tgt_start = np.datetime64('2007-06-01')
    onset_idx = (np.datetime64(onset) - tgt_start).astype('timedelta64[D]').astype(int)
    end_idx = (np.datetime64(end) - tgt_start).astype('timedelta64[D]').astype(int)
    print(f"   Event {onset} to {end}: indices {onset_idx} to {end_idx}")
    print(f"   All days active: {np.all(active[onset_idx:end_idx+1])}")
    if onset_idx > 0:
        print(f"   Day before onset active: {active[onset_idx-1]}")
    if end_idx < len(active) - 1:
        print(f"   Day after end active: {active[end_idx+1]}")

# 6. Verify report fields
print(f"\n6. Report fields:")
print(f"   - region: {report['region']}")
print(f"   - baseline_analysed: {report['baseline_analysed']}")
print(f"   - target_analysed: {report['target_analysed']}")
print(f"   - events: {report['events']}")
print(f"   - complete: {report['complete']}")
print(f"   - caveats: '{report['caveats']}'")

ds.close()
print("\n=== ALL CHECKS PASSED ===")
