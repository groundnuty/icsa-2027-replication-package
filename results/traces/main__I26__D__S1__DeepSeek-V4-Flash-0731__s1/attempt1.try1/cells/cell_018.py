import h5py
import numpy as np
from datetime import datetime, timedelta

f = h5py.File('/work/sst_s2.nc', 'r')

# Read time values
time_raw = f['time'][:]
print("Time dtype:", time_raw.dtype)
print("First few times:", time_raw[:5])
print("Last few times:", time_raw[-5:])
