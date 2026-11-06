import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Define region and period
LAT_MIN, LAT_MAX = 54.39, 55.59
LON_MIN, LON_MAX = 18.25, 19.45
START_DATE = datetime(2021, 6, 1)
END_DATE = datetime(2021, 8, 31)
BASELINE_START = datetime(1992, 1, 1)
BASELINE_END = datetime(2002, 12, 31)

# Create output directory
os.makedirs('output', exist_ok=True)

print(f"Region: lat {LAT_MIN} to {LAT_MAX}°N, lon {LON_MIN} to {LON_MAX}°E")
print(f"Target period: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
print(f"Baseline period: {BASELINE_START.strftime('%Y-%m-%d')} to {BASELINE_END.strftime('%Y-%m-%d')}")