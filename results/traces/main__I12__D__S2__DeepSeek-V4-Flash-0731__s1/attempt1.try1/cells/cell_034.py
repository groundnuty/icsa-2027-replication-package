
import os
import xarray as xr
import json

# Verify files exist
print("output/mhw_mask.nc exists:", os.path.exists('output/mhw_mask.nc'))
print("output/report.json exists:", os.path.exists('output/report.json'))
print("File sizes:")
print(f"  mhw_mask.nc: {os.path.getsize('output/mhw_mask.nc')} bytes")
print(f"  report.json: {os.path.getsize('output/report.json')} bytes")

# Final validation of mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("\nmhw_mask.nc validation:")
print(f"  dims: {dict(ds.dims)}")
print(f"  mhw dtype: {ds['mhw'].dtype}")
print(f"  mhw shape: {ds['mhw'].shape}")
print(f"  unique values: {sorted(set(ds['mhw'].values.flatten()))}")
print(f"  time coords: {len(ds.time)} values, {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"  lat coords: {len(ds.latitude)} values, {ds.latitude.values[0]:.2f} to {ds.latitude.values[-1]:.2f}")
print(f"  lon coords: {len(ds.longitude)} values, {ds.longitude.values[0]:.2f} to {ds.longitude.values[-1]:.2f}")

# Final validation of report.json
with open('output/report.json') as f:
    report = json.load(f)
print("\nreport.json validation:")
print(f"  region: {report['region']}")
print(f"  baseline_analysed: {report['baseline_analysed']}")
print(f"  target_analysed: {report['target_analysed']}")
print(f"  events: {report['events']}")
print(f"  complete: {report['complete']}")
print(f"  caveats: '{report['caveats']}'")
