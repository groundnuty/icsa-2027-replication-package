import numpy as np, os, xarray as xr
print("numpy", np.__version__, "xarray", xr.__version__)
# verify hazen quantile semantics
x = np.arange(1., 11.)  # 1..10, n=10
q = np.quantile(x, 0.9, method="hazen")
# hazen: h = (n+1)*0.9 = 9.9 -> 0.1*x[9] + 0.9*x[10]? no: h=(n+1)p=9.9 -> between x_(9)=9 and x_(10)=10, frac .9
print("hazen:", q)  # expect 9.9
print("prev file still there:", os.path.exists('/work/data/sst_20160601.nc'))
