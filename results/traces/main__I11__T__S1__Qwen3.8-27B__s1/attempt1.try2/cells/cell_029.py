
import shutil, os
os.makedirs("/output", exist_ok=True)
shutil.copyfile("/work/output/mhw_mask.nc", "/output/mhw_mask.nc")
shutil.copyfile("/work/output/report.json", "/output/report.json")
print(sorted(os.listdir("/output")), sorted(os.listdir("/work/output")))

import warnings; warnings.filterwarnings("ignore")
import numpy as np, xarray as xr, json
ds = xr.open_dataset("output/mhw_mask.nc")
print(ds)
print("mhw dtype:", ds["mhw"].dtype, "dims:", ds["mhw"].dims)
print("time:", ds["time"].values[0], "->", ds["time"].values[-1], "n=", ds.sizes["time"])
print("lat:", ds["lat"].dtype, ds["lat"].values[0], "->", ds["lat"].values[-1])
print("lon:", ds["lon"].dtype, ds["lon"].values[0], "->", ds["lon"].values[-1])
m = ds["mhw"].values
print("mask sum:", int(m.sum()), "unique:", np.unique(m))
# per-day counts
pc = m.sum(axis=(1,2))
print("active days:", int((pc>0).sum()), "first/last active:", str(ds['time'].values[np.argmax(pc>0)][:10]), str(ds['time'].values[-(pc[::-1]>0).argmax()][:10]))
rpt = json.load(open("output/report.json"))
print("report keys:", sorted(rpt.keys()))
print("events:", rpt["events"])
# verify mask matches per-cell MHW recomputation on a random sample
percell = np.load("/work/percell.npy")
print("mask equals percell reshape:", bool((m == percell.reshape(92,60,60).astype(np.uint8)).all()))
