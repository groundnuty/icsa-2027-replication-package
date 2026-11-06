import numpy as np, pickle, json, os
import xarray as xr

with open("/tmp/sst_data.pkl","rb") as f: D = pickle.load(f)
with open("/tmp/mhw2_state.pkl","rb") as f: S = pickle.load(f)

mhw_cells = S["mhw_mask"]            # (92, nc)
cell_idx = S["cell_idx"]
events = S["events"]

# full-grid mask
mhw_grid = np.zeros((92, 60, 60), dtype=np.uint8)
flat = mhw_grid.reshape(92, 3600)
flat[:, cell_idx] = mhw_cells.astype(np.uint8)

# exact dataset coordinates
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
import pandas as pd
t = pd.to_datetime(ds["time"].values)
tmask = (t >= "2013-06-01") & (t <= "2013-08-31")
time_vals = ds["time"].values[tmask]          # datetime64[ns]
lat_vals = ds["latitude"].values[(ds["latitude"].values >= 57.85 - 1e-9) & (ds["latitude"].values <= 59.05 + 1e-9)]
lon_vals = ds["longitude"].values[(ds["longitude"].values >= 21.01 - 1e-9) & (ds["longitude"].values <= 22.21 + 1e-9)]
ds.close()
assert len(time_vals) == 92 and len(lat_vals) == 60 and len(lon_vals) == 60

os.makedirs("output", exist_ok=True)
out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_grid)},
    coords={"time": time_vals, "lat": lat_vals, "lon": lon_vals},
)
out["mhw"].attrs["description"] = "1 where the grid cell is inside a per-cell MHW (incl. merged gap days) on that day, 0 otherwise (land = 0)"
out.to_netcdf("output/mhw_mask.nc", engine="h5netcdf")
print("wrote output/mhw_mask.nc")

report = {
    "region": {"lat_min": 57.85, "lat_max": 59.05, "lon_min": 21.01, "lon_max": 22.21},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2013-06-01", "end": "2013-08-31"},
    "events": [{"onset": e[0], "end": e[1]} for e in events],
    "complete": True,
    "caveats": "",
}
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)
print("wrote output/report.json")
print(json.dumps(report, indent=2))

# summary stats
print("cells with any MHW day:", int(mhw_grid.any(axis=0).sum()))
print("event1 mask sum (Jun1-13):", int(mhw_grid[0:13].sum()), " event2 (Jun25-Jul1):", int(mhw_grid[24:31].sum()))
