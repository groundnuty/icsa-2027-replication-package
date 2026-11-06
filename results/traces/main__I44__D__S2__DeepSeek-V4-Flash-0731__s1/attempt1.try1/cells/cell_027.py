
import numpy as np
import pandas as pd
import json

# Load the output files
with open('/work/output/report.json', 'r') as f:
    report = json.load(f)

print("Report:")
print(json.dumps(report, indent=2))
print()

# Verify all dates
print(f"Target period: {report['target_analysed']['start']} to {report['target_analysed']['end']}")
print(f"Baseline used: {report['baseline_analysed']['start']} to {report['baseline_analysed']['end']}")

# Verify events
events = report['events']
print(f"\nEvents: {len(events)}")
for ev in events:
    print(f"  Onset: {ev['onset']}, End: {ev['end']}")
    
    # Verify dates are valid
    onset = pd.Timestamp(ev['onset'])
    end = pd.Timestamp(ev['end'])
    print(f"  Duration: {(end - onset).days + 1} days")
    assert onset <= end, "Event onset must be before end"
    assert onset >= pd.Timestamp('2004-06-01'), "Event onset must be within target period"
    assert end <= pd.Timestamp('2004-08-31'), "Event end must be within target period"

print("\nAll date validations passed!")

# Verify mhw_mask
import xarray as xr
ds_check = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
mhw = ds_check['mhw'].values
print(f"\nmhw_mask shape: {mhw.shape}")
print(f"mhw dtype: {mhw.dtype}")
print(f"Unique values: {np.unique(mhw)}")
print(f"MHW sum: {mhw.sum()}")

# Check which days have active cells
time_idx = ds_check.time.values
for t in range(len(time_idx)):
    if mhw[t].sum() > 0:
        date = pd.Timestamp(time_idx[t]).strftime('%Y-%m-%d')
        print(f"  {date}: {mhw[t].sum()} cells in MHW")
