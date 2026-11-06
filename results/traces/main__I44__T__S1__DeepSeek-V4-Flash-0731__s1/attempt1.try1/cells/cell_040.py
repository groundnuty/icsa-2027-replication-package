import numpy as np

# Load thresholds and check they're reasonable
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Find a central sea cell
sea_indices = np.argwhere(sea_mask)
center_idx = sea_indices[len(sea_indices)//2]
i, j = center_idx
print(f"Center sea cell: ({i}, {j})")

# Check threshold across DOYs
print("\nDOY   Threshold  Climatology")
for d in range(1, 367, 30):
    if d == 60:
        continue
    print(f"{d:4d}  {threshold_smooth[d, i, j]:10.4f}  {climatology_smooth[d, i, j]:10.4f}")

# Check day 60 specifically
print(f"{60:4d}  {threshold_smooth[60, i, j]:10.4f}  {climatology_smooth[60, i, j]:10.4f}")
print(f"{59:4d}  {threshold_smooth[59, i, j]:10.4f}  {climatology_smooth[59, i, j]:10.4f}")
print(f"{61:4d}  {threshold_smooth[61, i, j]:10.4f}  {climatology_smooth[61, i, j]:10.4f}")
