
import xarray as xr
import numpy as np

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')

# Find days where mhw=1
mhw = ds['mhw'].values  # (92, 60, 60)

# For each day, count cells in MHW
active_days = np.where(mhw.sum(axis=(1,2)) > 0)[0]
print(f"Active days (time indices): {active_days}")

# Get the dates
time_vals = ds['time'].values
print(f"Active dates: {time_vals[active_days]}")

# For the first active day, count cells
print(f"\nMHW cells on first active day: {mhw[active_days[0]].sum()}")
print(f"MHW cells on second active day: {mhw[active_days[1]].sum()}")
print(f"MHW cells on last active day: {mhw[active_days[-1]].sum()}")

# Check land cells are all 0
# Land cells are those not sea cells
target_sst = np.load('/tmp/target_sst_f64.npy')
n_time, n_lat, n_lon = target_sst.shape
sea_mask = np.load('/tmp/sea_mask.npy')
land_mask = ~sea_mask
print(f"\nLand cells: {land_mask.sum()}")
print(f"Land cell MHW values all 0: {np.all(mhw[:, land_mask] == 0)}")

# Verify sea cells have correct values
print(f"Sea cell MHW values: {np.unique(mhw[:, sea_mask])}")

# Verify time coordinates
print(f"\nTime values match target: {np.array_equal(time_vals, np.load('/tmp/target_times_full.npy'))}")

# Verify coordinates
lat = ds['lat'].values
lon = ds['lon'].values
print(f"Lat values: {lat[0]} to {lat[-1]}, count={len(lat)}")
print(f"Lon values: {lon[0]} to {lon[-1]}, count={len(lon)}")

# Verify region bounds
print(f"Region: lat [{lat.min()}, {lat.max()}], lon [{lon.min()}, {lon.max()}]")
print(f"All lat in [59.93, 61.13]: {np.all((lat >= 59.93) & (lat <= 61.13))}")
print(f"All lon in [18.69, 19.89]: {np.all((lon >= 18.69) & (lon <= 19.89))}")
