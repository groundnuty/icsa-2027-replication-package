
import numpy as np
import datetime

# Load data
cached_t = np.load('cache/target_data.npz')
target_dates = [datetime.date.fromordinal(int(d)) for d in np.load('cache/target_dates.npy')]
target_sst = {}
for d in target_dates:
    target_sst[d] = cached_t[d.strftime('%Y%m%d')]

threshold_sm = np.load('cache/threshold_smoothed.npy')

n_target = len(target_dates)
target_array = np.array([target_sst[d] for d in target_dates], dtype=np.float64)
sea_cells = np.all(np.isfinite(target_array), axis=0)

# Check: do all sea cells have finite threshold for all days?
# target_doy range is 153-244
sea_cells_count = sea_cells.sum()
print(f'Sea cells: {sea_cells_count}')

# Check threshold NaN for sea cells across all target days
for doy in range(153, 245):
    thr = threshold_sm[doy-1]
    nan_sea = np.isnan(thr) & sea_cells
    if nan_sea.any():
        print(f'  doy {doy}: {nan_sea.sum()} sea cells have NaN threshold')
        break
else:
    print('All sea cells have finite thresholds for all target days')
