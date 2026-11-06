import fsspec, sys
import numpy as np, xarray as xr
print("numpy", np.__version__, "xarray", xr.__version__, "python", sys.version.split()[0])
fs = fsspec.filesystem('onedata')
for p in ['icsa2027_data_20261101T090944Z/s1z', '/icsa2027_data_20261101T090944Z/s1z']:
    try:
        entries = fs.ls(p)
        print("OK path:", p, "n=", len(entries))
        for e in entries[:40]:
            print("  ", e)
        break
    except Exception as ex:
        print("fail", p, type(ex).__name__, str(ex)[:200])
