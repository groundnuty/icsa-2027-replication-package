
import os
import json

# Check output directory
print("Output files:")
for f in os.listdir('output'):
    filepath = os.path.join('output', f)
    size = os.path.getsize(filepath)
    print(f"  {f}: {size} bytes")

# Read back the report
with open('output/report.json', 'r') as f:
    report = json.load(f)

print("\nFinal Report:")
print(json.dumps(report, indent=2))

# Verify the NetCDF file is valid
import xarray as xr
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("\nFinal NetCDF check:")
print(f"  Dimensions: {dict(ds.sizes)}")
print(f"  Variable 'mhw': dtype={ds['mhw'].dtype}, shape={ds['mhw'].shape}")
print(f"  mhw values: 0-{ds['mhw'].max().values}, sum={ds['mhw'].sum().values}")
ds.close()

print("\nAll checks passed. Analysis complete.")
