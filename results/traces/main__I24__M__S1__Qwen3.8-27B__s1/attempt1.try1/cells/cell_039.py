import os, json
for f in ["output/mhw_mask.nc", "output/report.json"]:
    print(f, os.path.getsize(f), "bytes")
print()
print(open("output/report.json").read())
import xarray as xr
d = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print("dims:", dict(d.sizes), "| mhw dtype:", d["mhw"].dtype,
      "| time decoded:", d["time"].values[0], "->", d["time"].values[-1],
      "| ones per active day max:", int(d["mhw"].values.sum(axis=(1,2)).max()))
d.close()
