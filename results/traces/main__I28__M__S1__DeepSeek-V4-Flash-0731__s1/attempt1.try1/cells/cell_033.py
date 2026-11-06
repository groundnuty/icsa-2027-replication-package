
import numpy as np
import xarray as xr
from datetime import date, timedelta

# Load the mhw mask
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds['mhw'].values
time_coords = ds['time'].values
lat_coords = ds['lat'].values
lon_coords = ds['lon'].values
ds.close()

print("mhw shape:", mhw.shape)
print("Total MHW cell-days:", np.sum(mhw))

# Check active days
active = np.any(mhw, axis=(1,2))
print("\nActive days:")
for i in range(len(active)):
    if active[i]:
        n_cells = np.sum(mhw[i])
        print(f"  {np.datetime_as_string(time_coords[i], unit='D')}: {n_cells} cells in MHW")

# Verify events match active days
print("\nRegional events:")
events = [
    {"onset": "2013-06-01", "end": "2013-06-13"},
    {"onset": "2013-06-23", "end": "2013-07-10"}
]

# Verify each event is a maximal run of active days
i = 0
n = len(active)
while i < n:
    if active[i]:
        start = i
        while i < n and active[i]:
            i += 1
        onset = np.datetime_as_string(time_coords[start], unit='D')
        end = np.datetime_as_string(time_coords[i-1], unit='D')
        print(f"  Found event: {onset} to {end}")
    else:
        i += 1

# Check the gap between events
# Event 1: Jun 1-13 (indices 0-12), Event 2: Jun 23-Jul 10
# Check if there are active days between them
for i in range(13, 22):
    if active[i]:
        print(f"  WARNING: Active on day {i} ({np.datetime_as_string(time_coords[i], unit='D')})")
print(f"  Days 14-22 active: {np.any(active[13:22])}")

# Verify the first event starts on the first day of the target period
print(f"\nFirst day is active: {active[0]}")
print(f"Second day is active: {active[1]}")
