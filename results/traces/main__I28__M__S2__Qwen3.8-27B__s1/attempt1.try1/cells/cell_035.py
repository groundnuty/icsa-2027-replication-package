import xarray as xr, json
import numpy as np, pandas as pd

o = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print(o)
v = o["mhw"]
print("dtype:", v.dtype, "dims:", v.dims)
print("unique values:", np.unique(v.values))
print("time range:", pd.to_datetime(v.time.values)[0], pd.to_datetime(v.time.values)[-1], "n:", len(v.time))
print("lat:", v.lat.values[0], "...", v.lat.values[-1], "n:", len(v.lat))
print("lon:", v.lon.values[0], "...", v.lon.values[-1], "n:", len(v.lon))

# compare coords with source dataset
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
t = pd.to_datetime(ds["time"].values)
tm = (t >= "2013-06-01") & (t <= "2013-08-31")
print("time matches source:", (o["time"].values == ds["time"].values[tm]).all())
latm = (ds["latitude"].values >= 57.85-1e-9) & (ds["latitude"].values <= 59.05+1e-9)
lonm = (ds["longitude"].values >= 21.01-1e-9) & (ds["longitude"].values <= 22.21+1e-9)
print("lat matches source:", (o["lat"].values == ds["latitude"].values[latm]).all())
print("lon matches source:", (o["lon"].values == ds["longitude"].values[lonm]).all())
ds.close()

# per-day active from written file
daily = v.values.sum(axis=(1,2))
print("days with mask>0:", int((daily>0).sum()))
print("event1 days (idx0-12) sums:", daily[0:13].tolist())
print("event2 days (idx24-30) sums:", daily[24:31].tolist())
print("other days nonzero:", [i+1 for i in range(92) if daily[i] > 0 and not (i < 13 or 24 <= i <= 30)])

r = json.load(open("output/report.json"))
print("report keys:", sorted(r.keys()))
print("events:", r["events"])
print("OK")
