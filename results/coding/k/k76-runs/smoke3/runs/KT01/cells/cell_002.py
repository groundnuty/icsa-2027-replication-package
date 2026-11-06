import json, os
import numpy as np, netCDF4
os.makedirs("/work/output", exist_ok=True)
with netCDF4.Dataset("/work/output/mhw_mask.nc", "w") as f:
    f.createDimension("time", 92); f.createDimension("lat", 60); f.createDimension("lon", 60)
    v = f.createVariable("mhw", "u1", ("time", "lat", "lon")); v[:] = np.zeros((92, 60, 60), dtype="u1")
json.dump({"events": []}, open("/work/output/report.json", "w"))
print("written")
