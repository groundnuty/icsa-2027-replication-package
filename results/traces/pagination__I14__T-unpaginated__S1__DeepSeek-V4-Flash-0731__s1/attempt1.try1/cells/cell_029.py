
import numpy as np
import xarray as xr

# Check the output mask for land cells
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values
sea_mask = np.load('sea_mask.npy')

# Verify all land cells have mhw=0
for lat_i in range(60):
    for lon_i in range(60):
        if not sea_mask[lat_i, lon_i]:
            assert np.all(mhw[:, lat_i, lon_i] == 0), f"Land cell ({lat_i},{lon_i}) has non-zero mhw"

print("All land cells have mhw=0. ✓")

# Verify no sea cell has mhw where it shouldn't
# (sea cells should have mhw=1 only where per_cell_mhw is True)
per_cell_mhw = np.load('per_cell_mhw.npy')
for lat_i in range(60):
    for lon_i in range(60):
        if sea_mask[lat_i, lon_i]:
            expected = per_cell_mhw[:, lat_i, lon_i].astype(np.uint8)
            actual = mhw[:, lat_i, lon_i]
            assert np.all(expected == actual), f"Sea cell ({lat_i},{lon_i}) mismatch"

print("All sea cells match per_cell_mhw. ✓")

# Check the coordinate values match the dataset
print(f"Time: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"Lat: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"Lon: {ds.lon.values[0]} to {ds.lon.values[-1]}")
print(f"mhw dtype: {ds.mhw.dtype}")

ds.close()
