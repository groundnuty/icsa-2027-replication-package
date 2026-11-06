
import xarray as xr
import json

ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc:")
print(f"  dims: {ds_out.dims}")
print(f"  mhw dtype: {ds_out['mhw'].dtype}")
print(f"  mhw shape: {ds_out['mhw'].shape}")
print(f"  mhw values: {ds_out['mhw'].values.min()} to {ds_out['mhw'].values.max()}")
print(f"  Time: {ds_out.time.values[0]} to {ds_out.time.values[-1]}")

with open('output/report.json') as f:
    report = json.load(f)
print("\nreport.json:")
print(json.dumps(report, indent=2))

# Check events in the mask
mhw = ds_out['mhw'].values
n_target = mhw.shape[0]
# Count active days
for t in range(n_target):
    if mhw[t].sum() > 0:
        pass  # just checking

# Count active days
active = mhw.sum(axis=(1,2)) > 0
print("\nActive days in mask:", active.sum())
