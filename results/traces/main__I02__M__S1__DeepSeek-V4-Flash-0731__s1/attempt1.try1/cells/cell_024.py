
import numpy as np

threshold = np.load('/tmp/threshold_unsmoothed.npy')
climatology = np.load('/tmp/climatology_unsmoothed.npy')

def smooth_wrap(arr):
    """Smooth a (lat, lon, 366) array with a 31-day centered moving mean that wraps around.
    For day d (0-indexed), average days (d-15)%366 to (d+15)%366.
    """
    n_lat, n_lon, n_doy = arr.shape
    result = np.zeros_like(arr)
    
    # Create extended array: arr[-15:] + arr + arr[:15]
    # ext[:, :, k] = arr[:, :, (k - 15) % 366] for k in 0..(366+29)
    ext = np.concatenate([arr[:, :, -15:], arr, arr[:, :, :15]], axis=2)
    # ext shape: (n_lat, n_lon, 366 + 30) = (n_lat, n_lon, 396)
    
    # For day d (0-indexed), we want arr[(d-15)%366] ... arr[(d+15)%366]
    # In ext: ext[:, :, 0] = arr[:, :, -15] = arr[:, :, (0-15)%366]
    # ext[:, :, k] = arr[:, :, (k-15)%366]
    # So arr[(d-15)%366] = ext[:, :, d]
    # And arr[(d+15)%366] = ext[:, :, d+30]
    # We need ext[:, :, d:d+31]
    
    # Use cumulative sum
    cumsum = np.concatenate([np.zeros((n_lat, n_lon, 1)), np.cumsum(ext, axis=2)], axis=2)
    # cumsum[:, :, k] = sum of ext[:, :, 0:k]
    
    for d in range(n_doy):
        # Sum of ext[:, :, d] to ext[:, :, d+30]
        s = cumsum[:, :, d+31] - cumsum[:, :, d]
        result[:, :, d] = s / 31.0
    
    return result

print("Smoothing threshold...")
threshold_smoothed = smooth_wrap(threshold)
print("Smoothing climatology...")
climatology_smoothed = smooth_wrap(climatology)

print(f"Threshold smoothed shape: {threshold_smoothed.shape}")
print(f"Climatology smoothed shape: {climatology_smoothed.shape}")
print(f"Threshold smoothed NaN count: {np.isnan(threshold_smoothed).sum()}")
print(f"Climatology smoothed NaN count: {np.isnan(climatology_smoothed).sum()}")

# Verify with manual computation for first sea cell
sea_cells = []
for i in range(60):
    for j in range(60):
        if not np.isnan(threshold[i,j,0]):
            sea_cells.append((i,j))

i, j = sea_cells[0]
print(f"First sea cell: ({i},{j})")
for day_idx in [0, 1, 59, 60, 100, 365]:
    manual = np.mean([threshold[i,j,(day_idx+k)%366] for k in range(-15,16)])
    diff = abs(threshold_smoothed[i,j,day_idx] - manual)
    print(f"  Day {day_idx+1}: smoothed={threshold_smoothed[i,j,day_idx]:.10f}, manual={manual:.10f}, diff={diff:.2e}")

# Verify for land cells (should be NaN)
land_cell_found = False
for i in range(60):
    for j in range(60):
        if (i,j) not in sea_cells:
            print(f"Land cell ({i},{j}): all NaN in smoothed: {np.all(np.isnan(threshold_smoothed[i,j,:]))}")
            land_cell_found = True
            break
    if land_cell_found:
        break

# Save smoothed
np.save('/tmp/threshold.npy', threshold_smoothed)
np.save('/tmp/climatology.npy', climatology_smoothed)
print("Saved smoothed thresholds and climatologies")
