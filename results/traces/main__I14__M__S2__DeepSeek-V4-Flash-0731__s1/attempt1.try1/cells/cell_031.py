
import xarray as xr
import numpy as np

# Load the output NetCDF
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw_out = ds['mhw'].values
ds.close()

# Load the computed mask
mhw_mask = np.load('/tmp/mhw_mask.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Reconstruct the full mask
n_target, n_lat, n_lon = 92, 60, 60
mhw_full = np.zeros((n_target, n_lat, n_lon), dtype=np.uint8)
for ci in range(len(sea_cells)):
    lat, lon = sea_cells[ci]
    mhw_full[:, lat, lon] = mhw_mask[ci, :]

# Compare
match = np.array_equal(mhw_out, mhw_full)
print("Output matches computed mask:", match)

if not match:
    diff = np.where(mhw_out != mhw_full)
    print("Differences at:", len(diff[0]), "locations")
    for i in range(min(10, len(diff[0]))):
        t, lat, lon = diff[0][i], diff[1][i], diff[2][i]
        print(f"  ({t},{lat},{lon}): output={mhw_out[t,lat,lon]}, computed={mhw_full[t,lat,lon]}")
