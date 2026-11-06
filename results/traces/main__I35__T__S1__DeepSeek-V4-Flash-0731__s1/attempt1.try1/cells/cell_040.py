
import numpy as np

threshold_raw = np.load('/tmp/threshold_raw.npy')
climatology_raw = np.load('/tmp/climatology_raw.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')

# Verify smoothing for a specific cell and day
# Sea cell: pick one that we know has finite values
target_sst = np.load('/tmp/target_sst.npy')
n_time, n_lat, n_lon = target_sst.shape
sea_mask = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_mask[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

# Find a sea cell
sea_cells = np.argwhere(sea_mask)
si, sj = sea_cells[0]
print(f"Testing cell ({si},{sj})")

# Manual smoothing for day 153 (index 152)
d = 152  # 0-indexed for day 153
n = 366
half = 15

# Manual computation
manual = np.zeros((n_lat, n_lon))
for offset in range(-half, half+1):
    idx = (d + offset) % n
    manual += threshold_raw[idx]
manual /= 31

# Compare with stored smoothed value
diff = np.abs(manual[si, sj] - threshold_smooth[d, si, sj])
print(f"Manual smooth for cell ({si},{sj}), day 153: {manual[si, sj]}")
print(f"Stored smooth: {threshold_smooth[d, si, sj]}")
print(f"Difference: {diff}")
print(f"Match: {diff < 1e-10}")

# Test wrap-around: day 1 (index 0)
d = 0  # day 1
manual = np.zeros((n_lat, n_lon))
for offset in range(-half, half+1):
    idx = (d + offset) % n
    manual += threshold_raw[idx]
manual /= 31

diff = np.abs(manual[si, sj] - threshold_smooth[0, si, sj])
print(f"\nWrap-around check for day 1:")
print(f"Manual: {manual[si, sj]}, Stored: {threshold_smooth[0, si, sj]}, Diff: {diff}")
print(f"Match: {diff < 1e-10}")

# Test day 366 (index 365)
d = 365
manual = np.zeros((n_lat, n_lon))
for offset in range(-half, half+1):
    idx = (d + offset) % n
    manual += threshold_raw[idx]
manual /= 31

diff = np.abs(manual[si, sj] - threshold_smooth[365, si, sj])
print(f"\nDay 366 check:")
print(f"Manual: {manual[si, sj]}, Stored: {threshold_smooth[365, si, sj]}, Diff: {diff}")
print(f"Match: {diff < 1e-10}")
