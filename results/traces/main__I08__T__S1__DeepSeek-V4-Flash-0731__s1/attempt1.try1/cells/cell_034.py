
import numpy as np
import xarray as xr
import json

# Load the output files
ds = xr.open_dataset('output/mhw_mask.nc')
print("=== NetCDF verification ===")
print("Dimensions:", dict(ds.dims))
print("Coordinates:", list(ds.coords))
print("mhw dtype:", ds['mhw'].dtype)
print("mhw shape:", ds['mhw'].shape)
print("Time range:", str(ds['time'].values[0])[:10], "to", str(ds['time'].values[-1])[:10])
print("Lat range:", ds['lat'].values[0], "to", ds['lat'].values[-1], "n =", len(ds['lat']))
print("Lon range:", ds['lon'].values[0], "to", ds['lon'].values[-1], "n =", len(ds['lon']))
print("mhw unique values:", np.unique(ds['mhw'].values))
print("mhw total ones:", ds['mhw'].values.sum())

# Verify specific cell (0,0) MHW pattern
print("\n=== Cell (0,0) MHW pattern ===")
for t in range(30):
    print(f"Day {t}: {str(ds['time'].values[t])[:10]}, mhw = {ds['mhw'].values[t, 0, 0]}")

print("\n=== Report verification ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))

# Verify events match the active days analysis
mhw_data = ds['mhw'].values
n_time = mhw_data.shape[0]
active = np.array([np.any(mhw_data[t] > 0) for t in range(n_time)])
active_days = np.where(active)[0]
print(f"\nActive day indices: {active_days[0]} to {active_days[-1]}" if len(active_days) > 0 else "No active days")
print(f"First active date: {str(ds['time'].values[active_days[0]])[:10]}")
print(f"Last active date: {str(ds['time'].values[active_days[-1]])[:10]}")
print(f"Number of active days: {len(active_days)}")
