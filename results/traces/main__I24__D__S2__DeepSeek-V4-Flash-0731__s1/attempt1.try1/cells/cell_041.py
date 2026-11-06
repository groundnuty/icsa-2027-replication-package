
import numpy as np

# Load raw and smoothed threshold
threshold_raw = np.load('/work/threshold_raw.npy')
threshold_smooth = np.load('/work/threshold_smooth.npy')

# Sea cell for testing
target_sst = np.load('/work/target_sst.npy')
sea_cells = np.all(np.isfinite(target_sst), axis=0)
lat_i, lon_i = np.where(sea_cells)[0][0], np.where(sea_cells)[1][0]

# Verify smoothing for doy 1 (index 0)
# Should average indices (0-15)%366 to (0+15)%366 = 351, 352, ..., 365, 0, 1, ..., 15
indices = [(0 + offset) % 366 for offset in range(-15, 16)]
print(f"Indices for doy 1 smoothing: {indices}")
print(f"  First 5: {indices[:5]}, last 5: {indices[-5:]}")
print(f"  Count: {len(indices)}")

manual = np.mean(threshold_raw[indices, lat_i, lon_i])
numpy_result = threshold_smooth[0, lat_i, lon_i]
print(f"Manual smoothed: {manual:.6f}")
print(f"Numpy smoothed: {numpy_result:.6f}")
print(f"Match: {abs(manual - numpy_result) < 1e-10}")

# Verify smoothing for doy 366 (index 365)
indices = [(365 + offset) % 366 for offset in range(-15, 16)]
print(f"\nIndices for doy 366 smoothing: {indices[:5]} ... {indices[-5:]}")
print(f"  Count: {len(indices)}")

manual = np.mean(threshold_raw[indices, lat_i, lon_i])
numpy_result = threshold_smooth[365, lat_i, lon_i]
print(f"Manual smoothed: {manual:.6f}")
print(f"Numpy smoothed: {numpy_result:.6f}")
print(f"Match: {abs(manual - numpy_result) < 1e-10}")
