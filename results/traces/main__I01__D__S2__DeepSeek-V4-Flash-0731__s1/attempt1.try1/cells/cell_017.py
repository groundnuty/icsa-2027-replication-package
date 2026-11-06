
import numpy as np
import xarray as xr
import json

# Final verification of all outputs
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds_out.mhw.values

# Check land cells are 0
# Land cells are cells that are NOT sea cells. We can identify them by having NaN SST on at least one target day.
# Let's re-check by comparing with original data

# Load original data to verify
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat_sel = ds.latitude.values
lon_sel = ds.longitude.values
lat_idx = np.where((lat_sel >= 54.13) & (lat_sel <= 55.33))[0]
lon_idx = np.where((lon_sel >= 14.67) & (lon_sel <= 15.87))[0]

tgt_start = np.datetime64('2008-06-01')
tgt_end = np.datetime64('2008-08-31')
t_idx_tgt = np.where((ds.time.values >= tgt_start) & (ds.time.values <= tgt_end))[0]
tgt_sst = ds.analysed_sst.isel(time=t_idx_tgt, latitude=lat_idx, longitude=lon_idx).values

sea_cells = np.all(~np.isnan(tgt_sst), axis=0)
print("Sea cells in original data:", sea_cells.sum())

# Check that mhw mask is 0 for land cells
land_mask = ~sea_cells
if land_mask.any():
    land_values = mhw[:, land_mask]
    print("Land cell mhw values:", np.unique(land_values))
    assert np.all(land_values == 0), "Land cells should have mhw = 0"
    print("✓ All land cells have mhw = 0")
else:
    print("No land cells in region")

# Verify that sea cells can have mhw = 1
sea_mask = sea_cells
sea_values = mhw[:, sea_mask]
print("Sea cell mhw value distribution:", np.unique(sea_values, return_counts=True))

# Verify time dimension
print("\nTime dimension:", len(ds_out.time), "days")
print("First:", str(ds_out.time.values[0])[:10], "Last:", str(ds_out.time.values[-1])[:10])

# Check report
with open('output/report.json') as f:
    report = json.load(f)
print("\nReport fields:", sorted(report.keys()))
print("Complete:", report['complete'])

# Verify baseline_analysed includes the extended windows
print("Baseline analysed:", report['baseline_analysed'])

# Count total number of 1s in mask
print("\nTotal 1s in mhw mask:", mhw.sum())
print("Fraction of cells that are sea:", sea_cells.mean())
