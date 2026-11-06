
import xarray as xr
import json

# Read back the output files
ds_check = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(ds_check)
print("dims:", dict(ds_check.sizes))
print("mhw dtype:", ds_check.mhw.dtype)
print("mhw shape:", ds_check.mhw.shape)
print("mhw values range:", ds_check.mhw.values.min(), "-", ds_check.mhw.values.max())
print("Time coords:", ds_check.time.values[:3], "...", ds_check.time.values[-3:])
print("Lat coords:", ds_check.lat.values[:3], "...", ds_check.lat.values[-3:])
print("Lon coords:", ds_check.lon.values[:3], "...", ds_check.lon.values[-3:])

print("\n=== report.json ===")
with open('output/report.json') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))
