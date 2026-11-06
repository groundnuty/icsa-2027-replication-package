import numpy as np, pandas as pd, xarray as xr, json
ds = xr.open_dataset("output/mhw_mask.nc")
print(ds)
print("dtype:", ds["mhw"].dtype, "dims:", dict(ds.sizes))
t = pd.to_datetime(ds.time.values)
print("time:", t[0].date(), "->", t[-1].date(), "n=", len(t))
print("lat:", ds.latitude.values[0], "...", ds.latitude.values[-1], "n=", len(ds.latitude))
print("lon:", ds.longitude.values[0], "...", ds.longitude.values[-1], "n=", len(ds.longitude))
m = ds["mhw"].values
print("mhw sum:", int(m.sum()), "max:", int(m.max()))
# cross-check against stored work arrays
wt = np.load("work/target.npz"); wm = np.load("work/mhw.npy")
print("mhw matches work array:", np.array_equal(m, wm))
print("lat coords match dataset slice:", np.array_equal(ds.latitude.values, wt["lat"]),
      "| lon:", np.array_equal(ds.longitude.values, wt["lon"]),
      "| time:", np.array_equal(t.values, wt["time"]))
# active days recompute
active = m.astype(bool).any(axis=(1,2))
evs = []
i = 0
while i < 92:
    if active[i]:
        j = i
        while j+1 < 92 and active[j+1]: j += 1
        evs.append((str(t[i].date()), str(t[j].date()))); i = j+1
    else: i += 1
print("events from file:", evs)
rep = json.load(open("output/report.json"))
print("report events:", rep["events"])
print("land cells all zero:", bool((m[:, ~wt["sea"]].sum(axis=0) == 0).all()))
print("sea cells with any mhw:", int((m[:, wt["sea"].flat.reshape(60,60)].sum(axis=(0,2)) > 0).sum()))
print("files ok")
