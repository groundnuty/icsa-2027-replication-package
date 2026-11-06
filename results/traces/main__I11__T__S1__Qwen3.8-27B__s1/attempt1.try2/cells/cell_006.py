
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
print(fs.__class__, fs.__class__.__module__)
print([m for m in dir(fs) if not m.startswith('_')])
