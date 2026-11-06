import xarray as xr
import fsspec
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

fs = fsspec.filesystem('onedata')
file_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(file_path, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")

print(ds)
print(ds.coords)
