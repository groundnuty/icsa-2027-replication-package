
import xarray as xr
import numpy as np

ds = xr.open_dataset('output/mhw_mask.nc')
print("File structure:")
print(ds)
print(f"\nVariable mhw: dtype={ds['mhw'].dtype}, dims={ds['mhw'].dims}")

# Check some specific days
# Day 0 (June 1): should have no MHW cells
day0 = ds['mhw'].isel(time=0).values
print(f"\nDay 0 (2014-06-01): {day0.sum()} cells in MHW")

# Day 3 (June 4): should have 302 cells in MHW
day3 = ds['mhw'].isel(time=3).values
print(f"Day 3 (2014-06-04): {day3.sum()} cells in MHW")

# Day 19 (June 20): should have 8 cells in MHW
day19 = ds['mhw'].isel(time=19).values
print(f"Day 19 (2014-06-20): {day19.sum()} cells in MHW")

# Day 35 (July 6): should have 1398 cells in MHW
day35 = ds['mhw'].isel(time=35).values
print(f"Day 35 (2014-07-06): {day35.sum()} cells in MHW")

# Day 91 (August 31): should have 0 cells in MHW
day91 = ds['mhw'].isel(time=91).values
print(f"Day 91 (2014-08-31): {day91.sum()} cells in MHW")

# Verify coordinate values match the original dataset
print(f"\nTime range: {ds['time'].values[0]} to {ds['time'].values[-1]}")
print(f"Lat range: {ds['lat'].values[0]} to {ds['lat'].values[-1]}")
print(f"Lon range: {ds['lon'].values[0]} to {ds['lon'].values[-1]}")
