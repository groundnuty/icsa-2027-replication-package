
import numpy as np
import xarray as xr
from datetime import datetime, timedelta

# Load data
baseline_data = xr.open_dataset('baseline_data.nc')
target_data = xr.open_dataset('target_data.nc')

baseline_sst = baseline_data.analysed_sst.values
baseline_time = baseline_data.time.values
target_sst = target_data.analysed_sst.values
target_time = target_data.time.values

# Convert baseline_time to Python datetimes
baseline_dates = [datetime.utcfromtimestamp(t.astype('datetime64[us]').astype(np.int64) / 1e6) for t in baseline_time]
# Or better:
baseline_dates = [pd.Timestamp(t).to_pydatetime() for t in baseline_time]
