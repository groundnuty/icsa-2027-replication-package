
import os
import xarray as xr
import json

# Verify output files exist
print("Output files:")
for f in os.listdir('output'):
    path = os.path.join('output', f)
    size = os.path.getsize(path)
    print(f"  {f}: {size} bytes")

# Verify the mhw_mask.nc content
print("\n=== mhw_mask.nc ===")
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"Dimensions: {dict(ds.sizes)}")
print(f"Variables: {list(ds.data_vars)}")
print(f"Coordinates: {list(ds.coords)}")
print(f"mhw dtype: {ds['mhw'].dtype}")
print(f"mhw sum: {int(ds['mhw'].sum())}")
print(f"mhw min/max: {int(ds['mhw'].min())}/{int(ds['mhw'].max())}")
print(f"Time: {ds['time'].values[0]} to {ds['time'].values[-1]}")
print(f"Lat: {ds['lat'].values[0]} to {ds['lat'].values[-1]}")
print(f"Lon: {ds['lon'].values[0]} to {ds['lon'].values[-1]}")
ds.close()

# Verify report.json content
print("\n=== report.json ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))

# Verify that mhw_mask matches the computed mask
mhw_mask = np.load('mhw_mask.npy')
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mask_from_nc = ds['mhw'].values
ds.close()
print(f"\nMask match: {np.array_equal(mhw_mask.astype(np.uint8), mask_from_nc)}")
print(f"Mask from npy sum: {mhw_mask.sum()}")
print(f"Mask from nc sum: {mask_from_nc.sum()}")
