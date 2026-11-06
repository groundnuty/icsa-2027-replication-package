import numpy as np, xarray as xr, scipy
print("numpy", np.__version__, "xarray", xr.__version__)
# check numpy quantile method support
a = np.arange(1, 122, dtype=float)
print(np.quantile(a, 0.9, method="hazen"))
