import fsspec
import numpy as np
import xarray as xr
from datetime import datetime, timedelta
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
tt = ds.time.values.astype('datetime64[ns]')
idx = {str(d): i for i, d in enumerate(tt)}
deltas = np.diff(tt.astype('int64'))
bad = np.where(deltas != 86400000000000)[0]
print("num gaps:", len(bad))
for i in bad:
    print(str(tt[i]), "->", str(tt[i+1]), "gap days:", deltas[i]/86400000000000)
