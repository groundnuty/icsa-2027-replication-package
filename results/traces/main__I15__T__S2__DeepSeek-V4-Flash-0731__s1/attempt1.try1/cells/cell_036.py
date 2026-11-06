
import xarray as xr
import numpy as np

# Verify specific values in the mask
ds = xr.open_dataset('output/mhw_mask.nc')
mhw = ds.mhw.values

# Cell (0,0) on June 24 (should be 1) and June 23 (should be 0)
# June 24 2019 is day index 23 (June 1 is index 0)
print('Cell (0,0), June 23:', mhw[22, 0, 0])
print('Cell (0,0), June 24:', mhw[23, 0, 0])
print('Cell (0,0), July 2:', mhw[31, 0, 0])
print('Cell (0,0), July 3:', mhw[32, 0, 0])

# Check a land cell
sea_cells = np.load('sea_cells.npy')
land_cells = ~sea_cells
print('\nLand cells count:', land_cells.sum())
if land_cells.any():
    # Find first land cell
    idx = np.where(land_cells)
    li, lj = idx[0][0], idx[1][0]
    print(f'Land cell ({li},{lj}): all values should be 0')
    print('  Max value:', mhw[:, li, lj].max())

ds.close()
