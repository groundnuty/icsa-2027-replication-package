
import numpy as np

# Check climatology too
climatology_raw = np.load('output/climatology_raw.npy')
sea_cells = np.load('output/sea_cells.npy')

clim_with_d60 = climatology_raw.copy()
clim_with_d60[59] = (climatology_raw[58] + climatology_raw[60]) / 2.0

nan_in_clim = np.zeros((366, 60, 60), dtype=bool)
for d in range(366):
    for lat in range(60):
        for lon in range(60):
            if sea_cells[lat, lon] and np.isnan(clim_with_d60[d, lat, lon]):
                nan_in_clim[d, lat, lon] = True

days_with_nan = np.where(nan_in_clim.any(axis=(1, 2)))[0]
print(f"Days with NaN in climatology for some sea cell: {len(days_with_nan)}")

# Also check the smoothed values for the target period
threshold_smooth = np.load('output/threshold_smooth.npy')
climatology_smooth = np.load('output/climatology_smooth.npy')

# Check smoothed threshold for sea cells in target day range (doy 153-244, indices 152-243)
for d in range(152, 244):
    for lat in range(60):
        for lon in range(60):
            if sea_cells[lat, lon] and np.isnan(threshold_smooth[d, lat, lon]):
                print(f"NaN in smoothed threshold: day {d+1}, cell ({lat},{lon})")
                break
        else:
            continue
        break
    else:
        continue
    break
else:
    print("No NaN in smoothed threshold for sea cells in target day range (153-244)")
