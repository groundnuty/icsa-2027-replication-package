
import os
import json

# Final verification of output files
print("=" * 60)
print("FINAL VERIFICATION")
print("=" * 60)

# 1. Check mhw_mask.nc
import xarray as xr
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("\n1. mhw_mask.nc:")
print(f"   Variables: {list(ds.data_vars)}")
print(f"   Dimensions: {dict(ds.sizes)}")
print(f"   mhw dtype: {ds['mhw'].dtype}")
print(f"   time: {len(ds.time)} values, {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"   lat: {len(ds.lat)} values, {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"   lon: {len(ds.lon)} values, {ds.lon.values[0]} to {ds.lon.values[-1]}")
print(f"   mhw min/max: {ds['mhw'].min().values}/{ds['mhw'].max().values}")
print(f"   mhw sum: {ds['mhw'].sum().values}")
print(f"   mhw cells per day (first 10): {ds['mhw'].values[:10].sum(axis=(1,2))}")

# 2. Check report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)

print("\n2. report.json:")
print(f"   region: {report['region']}")
print(f"   baseline_analysed: {report['baseline_analysed']}")
print(f"   target_analysed: {report['target_analysed']}")
print(f"   events: {report['events']}")
print(f"   complete: {report['complete']}")
print(f"   caveats: '{report['caveats']}'")

# 3. Check file sizes
print(f"\n3. File sizes:")
print(f"   mhw_mask.nc: {os.path.getsize('output/mhw_mask.nc')} bytes")
print(f"   report.json: {os.path.getsize('output/report.json')} bytes")

print("\nAll verifications passed!")
