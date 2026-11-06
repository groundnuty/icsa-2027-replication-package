# Final verification of the output files
import xarray as xr
import json

print("=== FINAL VERIFICATION ===")

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc')
print(f"✓ mhw_mask.nc created successfully")
print(f"  Shape: {ds.mhw.shape}")
print(f"  Dimensions: {ds.dims}")
print(f"  Time range: {ds.time[0].values} to {ds.time[-1].values}")
print(f"  Lat range: {ds.lat.min().values} to {ds.lat.max().values}")
print(f"  Lon range: {ds.lon.min().values} to {ds.lon.max().values}")
ds.close()

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"✓ report.json created successfully")
print(f"  Region: {report['region']}")
print(f"  Events: {len(report['events'])}")
for i, event in enumerate(report['events']):
    print(f"    Event {i+1}: {event}")

print("\n=== TASK COMPLETED SUCCESSFULLY ===")