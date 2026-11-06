import numpy as np, json
from datetime import date, timedelta
import xarray as xr

z = np.load("/tmp/sst_data.npz")
T = z["T"]; ttimes = z["ttimes"]
s2 = np.load("/tmp/step2.npz")
thr_s = s2["thr_s"]; sea = s2["sea"]
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy(d): return cum[d.month-1] + d.day
tgt_doy = np.array([doy(date(int(str(t)[0:4]), int(str(t)[5:7]), int(str(t)[8:10]))) for t in ttimes]) - 1
T60 = T.reshape(92, 3600)
sea_idx = np.where(sea.ravel())[0]
hot = T60[:, sea_idx] >= thr_s[:, tgt_doy].T

flat = (77-48)*60 + (382-353)
pos = int(np.searchsorted(sea_idx, flat))
print("cell flat idx", flat, "is sea:", bool(sea.ravel()[flat]), "pos", pos)
print("SST 2021-07-15 (K):", T60[44, flat], "| thr:", thr_s[pos, 182], "| hot:", bool(hot[44, pos]))
print("SST - thr (K) on that day:", T60[44, flat] - thr_s[pos, 182])

# ---- verify output files ----
ds = xr.open_dataset("output/mhw_mask.nc")
print(ds)
m = ds["mhw"]
print("dtype:", m.dtype, "shape:", m.shape)
print("time:", str(m.time.values[0]), "..", str(m.time.values[-1]), "n=", m.time.size)
print("lat:", m.lat.values[0], "..", m.lat.values[-1], "n=", m.lat.size)
print("lon:", m.lon.values[0], "..", m.lon.values[-1], "n=", m.lon.size)
print("mhw sum:", int(m.values.sum()), "unique:", np.unique(m.values))
# land cells must be 0: compare with sea mask
latc = ds["lat"].values; lonc = ds["lon"].values
land = ~(np.isfinite(T).all(axis=0))  # same region layout
# recompute expected: sea cells had finite T; land = ~sea
sea_grid = sea  # (60,60) in file order (lat, lon)
print("land cells all zero:", bool((m.values[:, ~sea_grid] == 0).all()))
print("sea cell max:", int(m.values[:, sea_grid].max()))
# per-day counts in file vs our inmhw
print("per-day file counts (sample):", [int(m.values[i].sum()) for i in range(0, 92, 10)])

rep = json.load(open("output/report.json"))
print("report keys:", sorted(rep.keys()))
print(json.dumps(rep))
ds.close()
