
import warnings; warnings.filterwarnings("ignore")
import numpy as np, xarray as xr, json
ds = xr.open_dataset("output/mhw_mask.nc")
print(ds)
print("mhw dtype:", ds["mhw"].dtype, "dims:", ds["mhw"].dims)
print("time:", str(ds["time"].values[0]), "->", str(ds["time"].values[-1]), "n=", ds.sizes["time"])
print("lat:", ds["lat"].dtype, float(ds["lat"].values[0]), "->", float(ds["lat"].values[-1]))
print("lon:", ds["lon"].dtype, float(ds["lon"].values[0]), "->", float(ds["lon"].values[-1]))
m = ds["mhw"].values
print("mask sum:", int(m.sum()), "unique:", np.unique(m))
pc = m.sum(axis=(1,2))
aid = np.where(pc>0)[0]
print("active days:", len(aid), "first:", str(ds['time'].values[aid[0]])[:10], "last:", str(ds['time'].values[aid[-1]])[:10])
rpt = json.load(open("output/report.json"))
print("report keys:", sorted(rpt.keys()))
print("events:", rpt["events"], "complete:", rpt["complete"])
percell = np.load("/work/percell.npy")
print("mask equals percell reshape:", bool((m == percell.reshape(92,60,60).astype(np.uint8)).all()))
# raw file listing via netCDF4 to confirm single data variable + coords
import netCDF4
nc = netCDF4.Dataset("output/mhw_mask.nc")
print("variables:", {k: (str(v.dtype), v.shape) for k, v in nc.variables.items()})
nc.close()
