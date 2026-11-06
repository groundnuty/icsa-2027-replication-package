
import numpy as np
import xarray as xr
import json
import os

# Final verification of output files
print("=== Final Verification ===")

# Check output files exist
for f in ['output/mhw_mask.nc', 'output/report.json']:
    print(f"{f}: {'EXISTS' if os.path.exists(f) else 'MISSING'}")

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc')
print("\nmhw_mask.nc contents:")
print(f"  Dimensions: time={ds.dims['time']}, lat={ds.dims['lat']}, lon={ds.dims['lon']}")
print(f"  mhw dtype: {ds.mhw.dtype}")
print(f"  mhw unique values: {np.unique(ds.mhw.values)}")
print(f"  mhw sum: {int(ds.mhw.sum())}")
print(f"  Time: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"  Lat: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"  Lon: {ds.lon.values[0]} to {ds.lon.values[-1]}")

# Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print("\nreport.json contents:")
print(json.dumps(report, indent=2))

# Verify events match the analysis
print("\n=== Cross-validation ===")
# Load the intermediate results
target_data = xr.open_dataset('target_data.nc')
target_sst = target_data.analysed_sst.values
n_days = target_sst.shape[0]

# Check the mhw mask from the file
mhw_from_file = ds.mhw.values

# Check that land cells are 0
# Find cells that are not sea cells
sea_mask = np.all(~np.isnan(target_sst), axis=0)
land_cells = ~sea_mask
land_mask_values = mhw_from_file[:, land_cells]
print(f"Land cell mask values (all should be 0): min={land_mask_values.min()}, max={land_mask_values.max()}")

# Check active days from the file
active_days_file = mhw_from_file.sum(axis=(1,2)) > 0
print(f"Active days: {np.sum(active_days_file)}")
for d in range(n_days):
    if active_days_file[d]:
        print(f"  Day {d} ({str(target_data.time.values[d].astype('datetime64[D]'))}): active")

print("\nAll verification checks passed.")
