import fsspec, xarray as xr, numpy as np

fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
try:
    info = fs.info(path)
    print(info)
except Exception as e:
    print("info error:", e)
