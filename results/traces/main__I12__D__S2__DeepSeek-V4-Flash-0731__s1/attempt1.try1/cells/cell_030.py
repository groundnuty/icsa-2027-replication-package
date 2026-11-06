
import numpy as np
import pandas as pd
import xarray as xr

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
time = pd.to_datetime(ds.time.values)

lat_idx = np.where((lat >= 56.09) & (lat <= 57.29))[0]
lon_idx = np.where((lon >= 10.55) & (lon <= 11.75))[0]

mask = (time >= pd.Timestamp('1991-12-27')) & (time <= pd.Timestamp('2003-01-05'))
idx_base = np.where(mask)[0]
mask_t = (time >= pd.Timestamp('2009-06-01')) & (time <= pd.Timestamp('2009-08-31'))
idx_target = np.where(mask_t)[0]

base_sst = ds['analysed_sst'].isel(time=idx_base, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
target_sst = ds['analysed_sst'].isel(time=idx_target, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

# Check sea cells for NaN in baseline
n_lat, n_lon = 60, 60
sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_cells[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

# For sea cells, check if any baseline values are NaN
sea_cell_indices = np.where(sea_cells)
n_nan_cells = 0
for k in range(len(sea_cell_indices[0])):
    i, j = sea_cell_indices[0][k], sea_cell_indices[1][k]
    base_vals = base_sst[:, i, j]
    if np.any(np.isnan(base_vals)):
        n_nan_cells += 1
        if n_nan_cells <= 5:
            n_nan = np.sum(np.isnan(base_vals))
            print(f"Cell ({i},{j}): {n_nan} NaN values in baseline out of {len(base_vals)}")

print(f"\nTotal sea cells with NaN in baseline: {n_nan_cells}")
print(f"Total sea cells: {sea_cells.sum()}")
