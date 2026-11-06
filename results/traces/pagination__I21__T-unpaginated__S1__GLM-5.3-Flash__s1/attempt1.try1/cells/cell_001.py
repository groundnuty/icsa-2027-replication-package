import sys
print(sys.version)
import numpy as np, xarray as xr, fsspec
print("numpy", np.__version__)
print("xarray", xr.__version__)
try:
    import h5netcdf; print("h5netcdf", h5netcdf.__version__)
except Exception as e:
    print("h5netcdf missing:", e)

fs = fsspec.filesystem('onedata')
entries = None
for path in ['icsa2027_data_20261101T090944Z/s1z', '/icsa2027_data_20261101T090944Z/s1z']:
    try:
        entries = fs.ls(path)
        print("OK:", path, "n=", len(entries))
        base = path
        break
    except Exception as e:
        print("fail:", path, repr(e))

if entries:
    entries = sorted(entries)
    names = [e.split('/')[-1] for e in entries]
    print("first 10:", names[:10])
    print("last 5:", names[-5:])
    # sizes of a few
    for e in entries[:3]:
        try:
            print(fs.info(e))
        except Exception as ex:
            print("info fail", ex)
