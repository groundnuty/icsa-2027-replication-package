import numpy as np
import xarray as xr
import pandas as pd

mhw = np.load('/tmp/mhw_mask.npy')
target_ds = xr.open_dataset('/tmp/target_data.nc')
target_time = target_ds['time'].values
target_dates = [pd.Timestamp(t).to_pydatetime().date() for t in target_time]

# Check days around the event
for t in range(60, 80):
    n = mhw[t].sum()
    print(f"Day {t}: {target_dates[t]} - {n} cells in MHW")
