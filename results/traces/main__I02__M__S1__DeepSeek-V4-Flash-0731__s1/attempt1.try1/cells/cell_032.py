
import numpy as np

threshold = np.load('/tmp/threshold.npy')
climatology = np.load('/tmp/climatology.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Print some threshold values for a sea cell
# Find first sea cell
sea_cells = [(i,j) for i in range(60) for j in range(60) if sea_mask[i,j]]
print(f"Number of sea cells: {len(sea_cells)}")

# Check threshold values for DOYs 153-244 (target period)
i, j = sea_cells[0]
print(f"First sea cell: ({i},{j})")
print("Threshold values for target DOYs (153-244):")
for doy in [153, 160, 180, 200, 214, 220, 240, 244]:
    print(f"  DOY {doy}: threshold={threshold[i,j,doy-1]:.4f} K, climatology={climatology[i,j,doy-1]:.4f} K")

# Check SST values for target period at this cell
target_data = np.load('/tmp/target_data.npy')
print("\nSST values for target period at this cell:")
for t in range(0, 92, 10):
    print(f"  Day {t} (DOY {153+t}): SST={target_data[t,i,j]:.4f} K")

# Check if SST ever exceeds threshold
print("\nHot day check:")
hot = np.load('/tmp/hot.npy')
hot_days = np.where(hot[i,j,:])[0]
print(f"  Hot days: {hot_days}")
for t in hot_days:
    print(f"  Day {t}: SST={target_data[t,i,j]:.4f}, DOY={153+t}, threshold={threshold[i,j,153+t-1]:.4f}, hot={target_data[t,i,j] >= threshold[i,j,153+t-1]}")
