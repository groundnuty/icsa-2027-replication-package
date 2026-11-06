
import numpy as np

target_data = np.load('/tmp/target_data.npy')  # (92, 60, 60)
target_flat = target_data.reshape(92, -1)
thresh_smooth = np.load('/tmp/thresh_smooth.npy')  # (366, 3600)

# Sea cells: finite SST on every target day
sea_cells = ~np.any(np.isnan(target_flat), axis=0)
print('Sea cells:', sea_cells.sum())

# Cells with valid thresholds (all 366 days non-NaN)
thresh_valid = ~np.any(np.isnan(thresh_smooth), axis=0)
print('Cells with valid thresholds:', thresh_valid.sum())

# Are sea cells == cells with valid thresholds?
print('Sea cells == valid thresholds cells:', np.array_equal(sea_cells, thresh_valid))

# Check cells that are sea but not valid-threshold, or vice versa
diff1 = np.where(sea_cells & ~thresh_valid)[0]
diff2 = np.where(~sea_cells & thresh_valid)[0]
print('Sea but not valid-threshold:', len(diff1))
print('Valid-threshold but not sea:', len(diff2))

# Check cells that have any valid SST in target
any_valid_target = ~np.all(np.isnan(target_flat), axis=0)
print('Cells with any valid target SST:', any_valid_target.sum())

# For non-sea cells with valid thresholds: how many days have valid SST?
non_sea_valid_thresh = np.where(~sea_cells & thresh_valid)[0]
print('Non-sea cells with valid thresholds:', len(non_sea_valid_thresh))
for c in non_sea_valid_thresh[:10]:
    valid_days = np.sum(~np.isnan(target_flat[:, c]))
    print(f'  Cell {c}: {valid_days}/92 valid days')
