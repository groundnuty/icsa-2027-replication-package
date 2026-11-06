import numpy as np
import xarray as xr
import datetime as dt
import pandas as pd

# Load data
target_ds = xr.open_dataset('/tmp/target_data.nc')
target_sst = target_ds['analysed_sst'].values.astype(np.float64)
target_time = target_ds['time'].values
target_dates = [pd.Timestamp(t).to_pydatetime().date() for t in target_time]

threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

def day_of_year(date):
    y = date.year
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    month_days = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days[:date.month-1]) + date.day
    if not is_leap and date.month >= 3:
        doy += 1
    return doy

target_doy = [day_of_year(d) for d in target_dates]

# Find a sea cell that has an MHW
mhw = np.load('/tmp/mhw_mask.npy')
sea_with_mhw = np.argwhere(np.any(mhw, axis=0))

print(f"Cells with MHWs: {len(sea_with_mhw)}")
if len(sea_with_mhw) > 0:
    i, j = sea_with_mhw[0]
    print(f"First cell with MHW: ({i}, {j})")
    
    # Show hot days for this cell
    h = np.zeros(len(target_dates), dtype=bool)
    for t in range(len(target_dates)):
        doy = target_doy[t]
        h[t] = target_sst[t, i, j] >= threshold_smooth[doy, i, j]
    
    print("\nCell ({},{}) SST, threshold, hot status:".format(i, j))
    for t in range(len(target_dates)):
        doy = target_doy[t]
        thresh = threshold_smooth[doy, i, j]
        clim = climatology_smooth[doy, i, j]
        sst = target_sst[t, i, j]
        print(f"  {target_dates[t]} DOY={doy} SST={sst:.4f} Thresh={thresh:.4f} Clim={clim:.4f} Hot={h[t]} MHW={mhw[t,i,j]}")
