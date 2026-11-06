
import numpy as np

# Check data for inf values
baseline_sst = np.load('/tmp/baseline_sst.npy')
target_sst = np.load('/tmp/target_sst.npy')

print("Baseline SST inf count:", np.isinf(baseline_sst).sum())
print("Target SST inf count:", np.isinf(target_sst).sum())
print("Baseline SST NaN count:", np.isnan(baseline_sst).sum())
print("Target SST NaN count:", np.isnan(target_sst).sum())

# Check sea mask computed with isfinite
sea_mask_isfinite = np.all(np.isfinite(target_sst), axis=0)
sea_mask_isnan = ~np.isnan(target_sst).any(axis=0)
print("Sea cells (isfinite):", sea_mask_isfinite.sum())
print("Sea cells (~isnan):", sea_mask_isnan.sum())
print("Same:", np.array_equal(sea_mask_isfinite, sea_mask_isnan))
