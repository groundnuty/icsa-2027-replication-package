
import numpy as np
import pandas as pd

sst_target = np.load('sst_target.npy')
threshold_smooth = np.load('threshold_smooth.npy')
climatology_smooth = np.load('climatology_smooth.npy')
target_time = np.load('target_time.npy').astype('datetime64[D]').astype('datetime64[ns]')
lats = np.load('lats.npy')
lons = np.load('lons.npy')

print('Target SST shape:', sst_target.shape)
print('Target time shape:', target_time.shape)

# Step 1: Identify sea cells
# Cells with finite SST on every day of the target period
sea_cells = np.all(~np.isnan(sst_target), axis=0)
print('Sea cells:', sea_cells.sum(), 'out of', sea_cells.size)
print('Sea cell fraction:', sea_cells.sum() / sea_cells.size)

# Get target dates
target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
print('Target dates:', target_dates[0].isoformat(), 'to', target_dates[-1].isoformat())

def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

target_doy = np.array([day_of_year(d) for d in target_dates])
print('Target DOY range:', target_doy.min(), target_doy.max())
