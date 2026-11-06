
import numpy as np
import os
import xarray as xr
from datetime import date, timedelta

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

def load_region(date_obj):
    """Load the region data for a given date."""
    fname = f'sst_{date_obj.strftime("%Y%m%d")}.nc'
    path = os.path.join(data_dir, fname)
    ds = xr.open_dataset(path, engine='h5netcdf')
    data = ds['analysed_sst'].values[0, 34:94, 213:273].astype(np.float64)
    ds.close()
    return data

# Test with one date
d = date(1992, 1, 1)
data = load_region(d)
print(f"Shape: {data.shape}, dtype: {data.dtype}")
print(f"NaN count: {np.isnan(data).sum()}")
print(f"Sample: {data[:3,:3]}")
