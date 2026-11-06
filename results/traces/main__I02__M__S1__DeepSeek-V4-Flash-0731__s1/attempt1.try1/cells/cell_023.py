
import numpy as np

threshold = np.load('/tmp/threshold_unsmoothed.npy')
climatology = np.load('/tmp/climatology_unsmoothed.npy')
threshold_smoothed = np.load('/tmp/threshold.npy')
climatology_smoothed = np.load('/tmp/climatology.npy')

# Verify smoothing for the first sea cell
# Find first sea cell
sea_cells = []
for i in range(60):
    for j in range(60):
        if not np.isnan(threshold[i,j,0]):
            sea_cells.append((i,j))
print(f"First sea cell: {sea_cells[0]}")

i, j = sea_cells[0]
print(f"Cell ({i},{j})")
for day_idx in [0, 1, 59, 60, 100, 365]:
    manual = np.mean([threshold[i,j,(day_idx+k)%366] for k in range(-15,16)])
    print(f"  Day {day_idx+1}: smoothed={threshold_smoothed[i,j,day_idx]:.10f}, manual={manual:.10f}, diff={abs(threshold_smoothed[i,j,day_idx]-manual):.2e}")

# Also check that land cells are NaN
land_cells = [(i,j) for i in range(60) for j in range(60) if (i,j) not in sea_cells]
print(f"Land cells: {len(land_cells)}")
if land_cells:
    i, j = land_cells[0]
    print(f"  Land cell ({i},{j}): threshold_smoothed[0]={threshold_smoothed[i,j,0]}, all NaN: {np.all(np.isnan(threshold_smoothed[i,j,:]))}")
