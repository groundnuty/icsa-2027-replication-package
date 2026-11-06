
import os
import json

# Check output files exist
print("Output directory contents:")
for f in os.listdir('output'):
    path = os.path.join('output', f)
    size = os.path.getsize(path)
    print(f"  {f}: {size} bytes")

# Verify report.json structure
with open('output/report.json', 'r') as f:
    report = json.load(f)

required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
print("\nReport fields:", list(report.keys()))
print("All required fields present:", all(f in report for f in required_fields))

print("\nRegion:", report['region'])
print("Baseline analysed:", report['baseline_analysed'])
print("Target analysed:", report['target_analysed'])
print("Events:", report['events'])
print("Complete:", report['complete'])
print("Caveats:", repr(report['caveats']))

# Verify the events are sorted in time order
onsets = [e['onset'] for e in report['events']]
ends = [e['end'] for e in report['events']]
print("\nEvents onsets:", onsets)
print("Events ends:", ends)
print("Onsets sorted:", onsets == sorted(onsets))

# Verify mhw_mask.nc
import xarray as xr
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("\nNetCDF check:")
print("Dimensions:", dict(ds.sizes))
print("Variables:", list(ds.data_vars))
print("mhw dtype:", ds['mhw'].dtype)
print("mhw values range:", int(ds['mhw'].min()), "to", int(ds['mhw'].max()))
print("Time coords: first =", str(ds['time'].values[0])[:10], ", last =", str(ds['time'].values[-1])[:10])
print("Lat coords: first =", ds['lat'].values[0], ", last =", ds['lat'].values[-1])
print("Lon coords: first =", ds['lon'].values[0], ", last =", ds['lon'].values[-1])
ds.close()

print("\nAll checks passed!")
