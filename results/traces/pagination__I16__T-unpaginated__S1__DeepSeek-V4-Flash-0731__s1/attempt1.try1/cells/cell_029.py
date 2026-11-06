
import numpy as np

# Load the mhw_mask I computed earlier
mhw_mask = np.load('/tmp/mhw_mask.npy')  # (92, 3600)

# Verify mask values
print('Mask shape:', mhw_mask.shape)
print('Unique values:', np.unique(mhw_mask))
print('Total cells in MHW:', mhw_mask.sum())

# Check day 0 (June 1)
print('Day 0 MHW count:', (mhw_mask[0] > 0).sum())
# Check day 5 (June 6)
print('Day 5 MHW count:', (mhw_mask[5] > 0).sum())
# Check day 10 (June 11)
print('Day 10 MHW count:', (mhw_mask[10] > 0).sum())

# Check that all positive mask values are in sea cells
sea_cells = np.load('/tmp/sea_cells.npy')
for t in range(92):
    mhw_cells = np.where(mhw_mask[t] > 0)[0]
    for c in mhw_cells:
        if not sea_cells[c]:
            print(f'ERROR: Cell {c} in MHW on day {t} but not a sea cell')
            break
print('All MHW cells are sea cells')

# Verify the mask is 0 for all non-sea cells
non_sea = ~sea_cells
print('Non-sea cells with any MHW:', (mhw_mask[:, non_sea] > 0).sum())
