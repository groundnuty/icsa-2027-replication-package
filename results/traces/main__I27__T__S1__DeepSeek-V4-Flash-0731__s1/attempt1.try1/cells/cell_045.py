
import numpy as np

threshold_smooth = np.load('/tmp/threshold_smooth.npy')
clim_smooth = np.load('/tmp/clim_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Check some values for a sea cell
sea_indices = np.argwhere(sea_mask)
print("First few sea cells:", sea_indices[:5])

# Check a specific sea cell
for lat_i, lon_i in sea_indices[:3]:
    print(f"\nCell ({lat_i}, {lon_i}):")
    for doy in [1, 100, 150, 172, 200, 243, 300, 366]:
        idx = doy - 1
        print(f"  DOY {doy}: threshold={threshold_smooth[lat_i, lon_i, idx]:.3f}, clim={clim_smooth[lat_i, lon_i, idx]:.3f}")

# Check target data values for comparison
target_data = np.load('/tmp/target_data.npy')
print("\nTarget data range:", np.nanmin(target_data), "to", np.nanmax(target_data))
