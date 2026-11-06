
import numpy as np

# Load smoothed thresholds and climatology
thresh_smooth = np.load('/tmp/thresh_smooth.npy')  # (366, 3600)
clim_smooth = np.load('/tmp/clim_smooth.npy')  # (366, 3600)

# Check values for a sea cell (find one first)
sea_cells = np.load('/tmp/sea_cells.npy')
sea_cell_idx = np.where(sea_cells)[0][0]
print(f'First sea cell: flattened index {sea_cell_idx}, 2D index ({sea_cell_idx//60}, {sea_cell_idx%60})')

# Check threshold and climatology for this cell across a few days
for d in [153, 183, 213, 244]:  # June 1, July 1, Aug 1, Aug 31
    thr = thresh_smooth[d-1, sea_cell_idx]
    clim = clim_smooth[d-1, sea_cell_idx]
    print(f'DOY {d}: threshold={thr:.2f} K ({thr-273.15:.2f}°C), climatology={clim:.2f} K ({clim-273.15:.2f}°C)')

# Check overall stats
valid_thresh = thresh_smooth[~np.isnan(thresh_smooth)]
valid_clim = clim_smooth[~np.isnan(clim_smooth)]
print(f'\nThreshold range: {valid_thresh.min():.2f} to {valid_thresh.max():.2f} K')
print(f'Climatology range: {valid_clim.min():.2f} to {valid_clim.max():.2f} K')
print(f'Threshold mean: {valid_thresh.mean():.2f} K')
print(f'Climatology mean: {valid_clim.mean():.2f} K')
