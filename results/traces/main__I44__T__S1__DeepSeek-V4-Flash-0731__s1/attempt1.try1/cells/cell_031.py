import xarray as xr
import numpy as np
import json

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc')
print("Dataset:")
print(ds)
print("\nmhw shape:", ds['mhw'].shape)
print("mhw dtype:", ds['mhw'].dtype)
print("mhw min/max:", ds['mhw'].min().values, ds['mhw'].max().values)
print("mhw sum:", ds['mhw'].sum().values)

# Check time dimension
print("\nTime range:", ds['time'].values[0], "to", ds['time'].values[-1])
print("Number of time steps:", len(ds['time']))

# Check lat/lon
print("Lat range:", ds['lat'].values[0], "to", ds['lat'].values[-1])
print("Lon range:", ds['lon'].values[0], "to", ds['lon'].values[-1])
print("Lat count:", len(ds['lat']), "Lon count:", len(ds['lon']))

# Check dimensions match original dataset values
print("\nTime dtype:", ds['time'].dtype)

# Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print("\nReport:", json.dumps(report, indent=2))

# Verify report fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"
print("\nAll required fields present in report.json")

# Verify region values
assert report['region']['lat_min'] == 63.31
assert report['region']['lat_max'] == 64.51
assert report['region']['lon_min'] == 21.31
assert report['region']['lon_max'] == 22.51
print("Region values correct")

# Verify baseline_analysed
assert report['baseline_analysed']['start'] == '1991-12-27'
assert report['baseline_analysed']['end'] == '2003-01-05'
print("Baseline range correct")

# Verify target_analysed
assert report['target_analysed']['start'] == '2004-06-01'
assert report['target_analysed']['end'] == '2004-08-31'
print("Target range correct")
