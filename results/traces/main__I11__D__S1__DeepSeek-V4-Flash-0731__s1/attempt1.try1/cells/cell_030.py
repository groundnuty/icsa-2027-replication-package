
import numpy as np

# Load target SST
target_sst = np.load('/work/target_sst.npy')
sea_mask = np.load('/work/sea_mask.npy')

print(f"Sea cells: {sea_mask.sum()} out of {sea_mask.size}")

# Verify that sea cells have finite SST on every target day
for i in range(60):
    for j in range(60):
        if sea_mask[i, j]:
            assert np.all(~np.isnan(target_sst[:, i, j])), f"Sea cell ({i},{j}) has NaN on some target day"
        else:
            assert np.any(np.isnan(target_sst[:, i, j])), f"Non-sea cell ({i},{j}) has finite SST on all target days"

print("Sea cell verification passed!")

# Also verify: are there cells that are sometimes NaN but not always?
nan_counts = np.sum(np.isnan(target_sst), axis=0)
print(f"Cells with NaN counts: {np.unique(nan_counts, return_counts=True)}")
