import numpy as np, os, sys
print("numpy", np.__version__, "python", sys.version)
print("CWD:", os.getcwd())
import h5py
# check coordinate consistency across a few files and time coord
for f in ["sst_19920601.nc", "sst_20000229.nc", "sst_20120601.nc", "sst_19911231.nc"]:
    p = f"/data/icsa2027_data_20261101T090944Z/s1z/{f}"
    with h5py.File(p, "r") as fh:
        print(f, list(fh.keys()))
        lat = fh["latitude"][:]; lon = fh["longitude"][:]
        tv = fh["time"][:]
        sst = fh["analysed_sst"]
        print("  lat[435:437]", lat[435:437], "lon[487:489]", lon[487:489], "time", tv)
        print("  sst dtype", sst.dtype, "shape", sst.shape)
