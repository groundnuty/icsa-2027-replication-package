
import numpy as np
import pandas as pd
from datetime import date

def day_of_year_custom(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Load saved data
threshold = np.load('/tmp/threshold_smoothed.npy')
climatology = np.load('/tmp/climatology_smoothed.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
per_cell_mhw = np.load('/tmp/per_cell_mhw.npy')
tgt_data = np.load('/tmp/tgt_data.npy')
tgt_doy = np.load('/tmp/tgt_doy.npy')

# Cell (52, 14)
lat, lon = 52, 14

tgt_series = tgt_data[:, lat, lon]
thresh_series = threshold[tgt_doy - 1, lat, lon]
hot_series = tgt_series >= thresh_series

print(f"Cell ({lat}, {lon}):")
print(f"  SST values: {tgt_series}")
print(f"  Threshold: {thresh_series}")
print(f"  Hot: {hot_series.astype(int)}")
print(f"  Per-cell MHW: {per_cell_mhw[:, lat, lon].astype(int)}")
