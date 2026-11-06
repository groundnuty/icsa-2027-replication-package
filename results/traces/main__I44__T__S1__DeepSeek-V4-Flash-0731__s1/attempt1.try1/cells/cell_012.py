import numpy as np
import xarray as xr
import datetime as dt

# Load saved data
base_ds = xr.open_dataset('/tmp/base_data.nc')
target_ds = xr.open_dataset('/tmp/target_data.nc')

base_sst = base_ds['analysed_sst'].values.astype(np.float64)  # (4028, 60, 60)
target_sst = target_ds['analysed_sst'].values.astype(np.float64)  # (92, 60, 60)
base_time = base_ds['time'].values
target_time = target_ds['time'].values

# Convert datetime64 to python dates for easy manipulation
base_dates = [pd.Timestamp(t).to_pydatetime() for t in base_time]
# Actually let me use numpy datetime
base_dates = base_time.astype('datetime64[D]').astype(object)
print(base_dates[:5], base_dates[-5:])
