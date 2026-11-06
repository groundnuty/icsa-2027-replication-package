
import xarray as xr
import json

# Check mhw_mask.nc
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(ds_out)
print("\nDimensions:", dict(ds_out.dims))
print("Variable mhw dtype:", ds_out['mhw'].dtype)
print("mhw values range:", ds_out['mhw'].min().values, "to", ds_out['mhw'].max().values)
print("mhw sum:", ds_out['mhw'].sum().values)
print("Time range:", ds_out.time.values[0], "to", ds_out.time.values[-1])
print("Lat range:", ds_out.lat.values[0], "to", ds_out.lat.values[-1])
print("Lon range:", ds_out.lon.values[0], "to", ds_out.lon.values[-1])

# Check report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\n=== report.json ===")
print(json.dumps(report, indent=2))
