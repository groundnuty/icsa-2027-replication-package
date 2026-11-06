
import sys, numpy as np, xarray as xr, netCDF4
print(sys.version)
print("numpy:", np.__version__)
# verify hazen quantile behavior
v = np.arange(1., 11.)
print("nanquantile hazen p90:", np.nanquantile(v, 0.90, method='hazen'))  # expect x[7] + 0.6*(x[8]-x[7]) = 8 + 0.6 = 8.6
import os
print("cpu:", os.cpu_count())
