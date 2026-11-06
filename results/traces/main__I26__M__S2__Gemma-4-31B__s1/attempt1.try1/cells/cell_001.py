import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

# Dataset path
ds_path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

# Region and time bounds
lat_min, lat_max = 57.83, 59.03
lon_min, lon_max = 17.41, 18.61
target_start = '2007-06-01'
target_end = '2007-08-31'
baseline_start = '1992-01-01'
baseline_end = '2002-12-31'

# To account for +/- 5 days window around baseline
baseline_load_start = '1991-12-27'
baseline_load_end = '2003-01-05'

# Open dataset
ds = xr.open_dataset(ds_path, engine="h5netcdf")

# Print basic info to check variable names and coordinates
print(ds)
