import os
import glob
import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime, timedelta

data_dir = "/data/icsa2027_data_20261101T090944Z/s1z"
all_files = sorted(glob.glob(os.path.join(data_dir, "sst_*.nc")))

# Extract dates from filenames
dates = [datetime.strptime(f.split('_')[1].split('.')[0], "%Y%m%d") for f in all_files]
min_date = min(dates)
max_date = max(dates)
print(f"Data range: {min_date.date()} to {max_date.date()}")
