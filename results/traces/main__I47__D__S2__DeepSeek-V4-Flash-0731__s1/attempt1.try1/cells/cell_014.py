
import numpy as np
import pickle

base_data = np.load('/work/base_data.npy')
tgt_data = np.load('/work/tgt_data.npy')
with open('/work/pool_dates.pkl', 'rb') as f:
    pool_dates = pickle.load(f)

tgt_nan = np.isnan(tgt_data)
cell_tgt_nan = tgt_nan.any(axis=0)
sea_cells = ~cell_tgt_nan

# For sea cells, check if any pool has all-NaN
for d in [1, 59, 61, 153, 244, 305, 366]:
    idx = np.array(pool_dates[d])
    pool = base_data[idx]  # (121, 60, 60)
    pool_all_nan = np.all(np.isnan(pool), axis=0)  # (60,60)
    n_sea_with_allnan = (pool_all_nan & sea_cells).sum()
    print(f"d={d}: sea cells with all-NaN pool: {n_sea_with_allnan}")

# Check how many NaN per pool for sea cells
for d in [153, 244]:
    idx = np.array(pool_dates[d])
    pool = base_data[idx]
    nan_count = np.isnan(pool).sum(axis=0)  # (60,60)
    sea_nan = nan_count[sea_cells]
    print(f"d={d}: sea cells NaN count range: {sea_nan.min()} to {sea_nan.max()}, mean {sea_nan.mean():.1f}")
