
import xarray as xr
import json

# Final check
print("=== FINAL VERIFICATION ===\n")

# Verify NetCDF can be read back
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc loaded successfully")
print(f"  mhw variable: shape={ds['mhw'].shape}, dtype={ds['mhw'].dtype}")
print(f"  Time: {ds.time.values[0]} to {ds.time.values[-1]} ({len(ds.time)} days)")
print(f"  Lat: {ds.lat.values[0]} to {ds.lat.values[-1]} ({len(ds.lat)} cells)")
print(f"  Lon: {ds.lon.values[0]} to {ds.lon.values[-1]} ({len(ds.lon)} cells)")
print(f"  Values: {sorted(set(ds['mhw'].values.flatten().tolist()))}")
print(f"  Total MHW cell-days: {int(ds['mhw'].sum().values)}")
ds.close()

# Verify report
with open('output/report.json') as f:
    report = json.load(f)
print("\nreport.json loaded successfully")
print(f"  region: {report['region']}")
print(f"  baseline_analysed: {report['baseline_analysed']}")
print(f"  target_analysed: {report['target_analysed']}")
print(f"  events: {report['events']}")
print(f"  complete: {report['complete']}")
print(f"  caveats: '{report['caveats']}'")

print("\n=== ALL CHECKS PASSED ===")
