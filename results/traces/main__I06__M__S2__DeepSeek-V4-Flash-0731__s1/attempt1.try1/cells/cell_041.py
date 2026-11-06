
import xarray as xr
import numpy as np
import json

# Verify output files
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')

# Check cell (9,27) in the region: lat index 9, lon index 27
# This corresponds to lat=54.64, lon=16.6
print("Cell (9,27) MHW pattern:")
for d in range(92):
    val = ds_out['mhw'][d, 9, 27].values
    if val == 1:
        date = str(ds_out['time'][d].values)[:10]
        print(f"  {date}: mhw={val}")

print("\nCell (15,55) MHW pattern:")
for d in range(92):
    val = ds_out['mhw'][d, 15, 55].values
    if val == 1:
        date = str(ds_out['time'][d].values)[:10]
        print(f"  {date}: mhw={val}")

# Check a land cell (should be all 0)
# Find a land cell
sea_cells = np.load('/tmp/sea_cells.npy')
land_cells = np.where(~sea_cells)
print(f"\nLand cell ({land_cells[0][0]}, {land_cells[1][0]}): all zeros = {np.all(ds_out['mhw'][:, land_cells[0][0], land_cells[1][0]].values == 0)}")

# Verify total
print(f"\nTotal mhw=1 values: {ds_out['mhw'].sum().values}")

# Verify report
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport fields:", list(report.keys()))
print("Events:", report['events'])
print("Complete:", report['complete'])
print("Caveats:", report['caveats'])
