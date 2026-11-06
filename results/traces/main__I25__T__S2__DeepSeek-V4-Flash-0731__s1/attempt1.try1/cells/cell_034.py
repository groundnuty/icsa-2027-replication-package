
import numpy as np
import xarray as xr
import json
import os

# Verify the output files are correct
with xr.open_dataset('output/mhw_mask.nc') as ds:
    print("=== Final verification of mhw_mask.nc ===")
    print(f"  Shape: {ds['mhw'].shape}")
    print(f"  Dtype: {ds['mhw'].dtype}")
    print(f"  Dimensions: {dict(ds.dims)}")
    print(f"  Time coords: {ds.time.values[0]} to {ds.time.values[-1]}")
    print(f"  Time count: {len(ds.time.values)}")
    print(f"  Lat coords: {ds.lat.values[0]} to {ds.lat.values[-1]}")
    print(f"  Lon coords: {ds.lon.values[0]} to {ds.lon.values[-1]}")
    
    # Check that the coordinate values match the dataset
    print(f"\n  Lat values: {ds.lat.values}")
    print(f"  Lon values: {ds.lon.values}")
    
    # Check the mhw values for the active days
    mhw = ds['mhw'].values
    active_days = np.where(mhw.sum(axis=(1,2)) > 0)[0]
    print(f"\n  Active days (indices): {active_days}")
    print(f"  Active day counts: {mhw.sum(axis=(1,2))[active_days]}")
    
    # Verify a specific cell: cell 2146 should be in an MHW on day 17
    # Need to map cell 2146 to (lat, lon) coordinates
    sea_mask = np.load('output/sea_mask.npy')
    sea_indices = np.where(sea_mask)
    lat_i, lon_i = sea_indices[0][2146], sea_indices[1][2146]
    print(f"\n  Cell 2146 maps to lat_idx={lat_i}, lon_idx={lon_i}")
    print(f"  mhw value on day 17 at this cell: {mhw[17, lat_i, lon_i]}")
    print(f"  mhw values days 0-20 at this cell: {mhw[0:21, lat_i, lon_i]}")

print("\n")

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
    print("=== Final verification of report.json ===")
    print(json.dumps(report, indent=2))
