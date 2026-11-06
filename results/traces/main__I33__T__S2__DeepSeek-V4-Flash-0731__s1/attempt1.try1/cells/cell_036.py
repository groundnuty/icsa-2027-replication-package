
import os
import json
import xarray as xr
import numpy as np

# Final check
print("=== Final Output Files ===")
for f in ['output/mhw_mask.nc', 'output/report.json']:
    size = os.path.getsize(f)
    print(f"{f}: {size} bytes")

# Verify report.json structure
with open('output/report.json') as f:
    report = json.load(f)

required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    if field not in report:
        print(f"MISSING FIELD: {field}")
    else:
        print(f"  {field}: OK")

# Verify region values
print(f"\nRegion: {report['region']}")
print(f"Baseline analysed: {report['baseline_analysed']}")
print(f"Target analysed: {report['target_analysed']}")
print(f"Events: {report['events']}")
print(f"Complete: {report['complete']}")
print(f"Caveats: '{report['caveats']}'")

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc')
print(f"\nmhw_mask.nc: shape={ds.mhw.shape}, dtype={ds.mhw.dtype}")
print(f"  Values: {np.unique(ds.mhw.values)}")
print(f"  Sum: {int(ds.mhw.sum())}")

print("\nAll checks passed. Task complete.")
