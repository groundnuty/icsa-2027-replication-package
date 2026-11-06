
import numpy as np

# Load target data
target_sst = np.load('/work/target_sst.npy')  # (92, 60, 60)

# Sea cells: finite SST on every day of target period
sea_cells = ~np.isnan(target_sst).any(axis=0)  # (60, 60)
print(f"Sea cells: {sea_cells.sum()} out of {sea_cells.size}")
print(f"Land cells: {(~sea_cells).sum()}")

# Check if these cells have finite baseline data too
baseline_sst = np.load('/work/baseline_sst.npy')
sea_baseline_finite = np.isnan(baseline_sst[:, sea_cells]).sum()
total_baseline_sea = baseline_sst[:, sea_cells].size
print(f"Baseline NaN count in sea cells: {sea_baseline_finite}")
print(f"Total baseline values in sea cells: {total_baseline_sea}")
print(f"Fraction NaN: {sea_baseline_finite/total_baseline_sea:.6f}")

# Check if any sea cell has NaN in baseline
sea_cells_nan_baseline = np.isnan(baseline_sst[:, sea_cells]).any(axis=0)
print(f"Sea cells with any NaN in baseline: {sea_cells_nan_baseline.sum()}")

# Check per-day NaN in baseline for sea cells
baseline_sea = baseline_sst[:, sea_cells]  # (4028, n_sea)
nan_per_day = np.isnan(baseline_sea).sum(axis=1)
print(f"\nNaN per baseline day (among sea cells): min={nan_per_day.min()}, max={nan_per_day.max()}")
days_with_nan = (nan_per_day > 0).sum()
print(f"Days with any NaN in sea cells: {days_with_nan}")

# Check target NaN
target_sea = target_sst[:, sea_cells]
nan_per_target_day = np.isnan(target_sea).sum(axis=1)
print(f"\nNaN per target day (among sea cells): min={nan_per_target_day.min()}, max={nan_per_target_day.max()}")
