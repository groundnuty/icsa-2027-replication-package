
import numpy as np
import xarray as xr

# Load the output mask
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values

# Load target SST to identify land cells
target_sst = np.load('/work/target_sst.npy')
n_lat, n_lon = target_sst.shape[1], target_sst.shape[2]

# Land cells = cells with NaN on any target day
land_cells = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        if not np.all(np.isfinite(target_sst[:, i, j])):
            land_cells[i, j] = True

print(f"Land cells: {land_cells.sum()}")

# Check that land cells have mhw=0 everywhere
land_mhw = mhw[:, land_cells]
print(f"Land cell mhw values: {np.unique(land_mhw)}")
print(f"Max land cell mhw value: {land_mhw.max()}")

# Check that sea cells have mhw values of 0 or 1
sea_cells = ~land_cells
sea_mhw = mhw[:, sea_cells]
print(f"Sea cell mhw values: {np.unique(sea_mhw)}")
print(f"Sea cell mhw sum: {sea_mhw.sum()}")

# Verify report
import json
with open('output/report.json') as f:
    report = json.load(f)
print(f"\nReport: {json.dumps(report, indent=2)}")

# Check that the report has exactly the required fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
print(f"\nReport fields: {list(report.keys())}")
print(f"All required fields present: {all(f in report for f in required_fields)}")
print(f"Extra fields: {set(report.keys()) - set(required_fields)}")
