
import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat_idx = list(range(34, 94))
lon_idx = list(range(213, 273))

time = ds['time'].values
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
baseline_mask = (time >= baseline_start) & (time <= baseline_end)
baseline_time_idx = np.where(baseline_mask)[0]

# Load baseline data for region
baseline_sst = ds['analysed_sst'].isel(time=baseline_time_idx, latitude=lat_idx, longitude=lon_idx).values
print("Baseline SST shape:", baseline_sst.shape, "dtype:", baseline_sst.dtype)
print("Baseline dates:", ds['time'].values[baseline_time_idx[0]], "to", ds['time'].values[baseline_time_idx[-1]])
print("NaN count in baseline:", np.isnan(baseline_sst).sum())

# Get the baseline dates as Python date objects
baseline_dates = [pd.Timestamp(t).date() for t in ds['time'].values[baseline_time_idx]]
print("First few baseline dates:", baseline_dates[:3])
