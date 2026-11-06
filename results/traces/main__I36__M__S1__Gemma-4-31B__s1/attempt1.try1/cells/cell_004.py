import os
import glob
import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime, timedelta

data_dir = "/data/icsa2027_data_20261101T090944Z/s1z"
all_files = sorted(glob.glob(os.path.join(data_dir, "sst_*.nc")))

valid_files = []
dates = []
for f in all_files:
    fname = os.path.basename(f)
    parts = fname.split('_')
    if len(parts) == 2:
        date_str = parts[1].replace('.nc', '')
        try:
            d = datetime.strptime(date_str, "%Y%m%d")
            valid_files.append(f)
            dates.append(d)
        except ValueError:
            pass

if dates:
    print(f"Data range: {min(dates).date()} to {max(dates).date()}")
else:
    print("No valid files found.")
