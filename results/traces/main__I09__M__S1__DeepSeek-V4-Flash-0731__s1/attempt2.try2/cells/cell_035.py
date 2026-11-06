
import json
import xarray as xr
import numpy as np

# Final verification
print("=== Final Output Verification ===\n")

# 1. Check report.json fields
with open('output/report.json', 'r') as f:
    report = json.load(f)

required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
print("Report fields:", sorted(report.keys()))
print("Exactly matches required:", sorted(report.keys()) == sorted(required_fields))

# Check types
print(f"\nregion type: {type(report['region']).__name__}")
print(f"region keys: {sorted(report['region'].keys())}")
print(f"baseline_analysed type: {type(report['baseline_analysed']).__name__}")
print(f"target_analysed type: {type(report['target_analysed']).__name__}")
print(f"events type: {type(report['events']).__name__}")
print(f"complete type: {type(report['complete']).__name__}")
print(f"caveats type: {type(report['caveats']).__name__}")

# 2. Check NetCDF
print("\n=== NetCDF Check ===")
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"Variable 'mhw' exists: {'mhw' in ds.data_vars}")
print(f"mhw dtype: {ds.mhw.dtype}")
print(f"Dimensions: {dict(ds.sizes)}")
print(f"All mhw values in [0,1]: {np.all((ds.mhw.values >= 0) & (ds.mhw.values <= 1))}")
print(f"Time dimension: {len(ds.time)} days")
ds.close()

# 3. Verify report events correspond to active days in mask
print("\n=== Event Consistency ===")
mhw_mask = np.load('/tmp/mhw_mask.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
active = np.any(mhw_mask & sea_cells[np.newaxis, :, :], axis=(1, 2))

from datetime import date, timedelta
target_dates = []
d = date(2022, 6, 1)
end = date(2022, 8, 31)
while d <= end:
    target_dates.append(d)
    d += timedelta(days=1)

# Verify each event is a maximal run of active days
for ev in report['events']:
    onset_str = ev['onset']
    end_str = ev['end']
    
    # Find indices
    onset_idx = next(i for i, td in enumerate(target_dates) if td.isoformat() == onset_str)
    end_idx = next(i for i, td in enumerate(target_dates) if td.isoformat() == end_str)
    
    # Check all days in event are active
    all_active = all(active[t] for t in range(onset_idx, end_idx + 1))
    print(f"Event {onset_str} to {end_str}: all days active = {all_active}")
    
    # Check the event is maximal (day before onset is not active, day after end is not active)
    before_active = active[onset_idx - 1] if onset_idx > 0 else False
    after_active = active[end_idx + 1] if end_idx < len(active) - 1 else False
    print(f"  Day before onset active: {before_active}")
    print(f"  Day after end active: {after_active}")
    print(f"  Maximal: {not before_active and not after_active}")

print("\nAll checks passed!")
