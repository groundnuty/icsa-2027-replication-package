
import xarray as xr
import json

# Verify mhw_mask.nc
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc:")
print(ds_out)
print("dims:", ds_out.dims)
print("mhw dtype:", ds_out['mhw'].dtype)
print("mhw shape:", ds_out['mhw'].shape)
print("Time range:", ds_out.time.values[0], "to", ds_out.time.values[-1])
print("mhw values:", ds_out['mhw'].values.min(), "to", ds_out['mhw'].values.max())

# Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print("\nreport.json:")
print(json.dumps(report, indent=2))
