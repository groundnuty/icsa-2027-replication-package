import numpy as np, json, pandas as pd

z = np.load("work/sst.npz", allow_pickle=False)
base_dates = z["base_dates"].astype("datetime64[D]")
base64 = z["base_arr"].astype(np.float64).reshape(z["base_arr"].shape[0], -1)
st = np.load("work/stats.npz")
thr = st["thr"]; sea_idx = st["sea_idx"]
win_idx = np.load("work/win_idx.npy", allow_pickle=True).item()

cum = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366])
bd = pd.DatetimeIndex(base_dates.astype("datetime64[ns]"))
base_doy = cum[(bd.month - 1).to_numpy()] + bd.day.to_numpy()

B = base_dates.astype("int64")  # day counts
in_base = (base_dates >= np.datetime64("1992-01-01")) & (base_dates <= np.datetime64("2002-12-31"))

for d in [1, 59, 61, 153, 244, 366]:
    tb = B[in_base & (base_doy == d)]
    diff = np.abs(B[:, None] - tb[None, :])
    mask = (diff.min(axis=1) <= 5)
    brute = np.where(mask)[0]
    mine = win_idx[d]
    ok = np.array_equal(brute, mine)
    c = sea_idx[100]
    P = base64[brute, c]
    thr_check = np.quantile(P, 0.9, method="hazen")
    cli_check = P.mean()
    print(f"d={d}: membership identical: {ok}, n={len(brute)}, "
          f"thr(cell100) brute={thr_check:.6f} stored={thr[100, d-1]:.6f} match={np.isclose(thr_check, thr[100, d-1])}, "
          f"cli match={np.isclose(cli_check, st['cli'][100, d-1])}")

allpool = np.unique(np.concatenate([win_idx[d] for d in win_idx]))
print("pool date span:", base_dates[allpool[0]], "..", base_dates[allpool[-1]], "n distinct:", len(allpool))

import xarray as xr, os
ds = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
v = ds["mhw"]
print("nc: var mhw", v.dtype, v.dims, v.shape)
assert str(v.dtype) == "uint8" and v.dims == ("time", "latitude", "longitude") and v.shape == (92, 60, 60)
assert set(v.values.ravel()) <= {0, 1}
lat_ok = np.allclose(v["latitude"].values, z["lat"], rtol=0, atol=1e-6)
lon_ok = np.allclose(v["longitude"].values, z["lon"], rtol=0, atol=1e-6)
print("lat/lon coords equal to source values:", lat_ok, lon_ok)
tvals = v["time"].values
print("time count:", len(tvals), tvals[0], tvals[-1])
assert (np.diff(tvals) == np.timedelta64(1, "D")).all()
ds.close()

rep = json.load(open("output/report.json"))
need = {"region", "baseline_analysed", "target_analysed", "events", "complete", "caveats"}
assert set(rep.keys()) == need, rep.keys()
assert set(rep["region"].keys()) == {"lat_min", "lat_max", "lon_min", "lon_max"}
assert isinstance(rep["complete"], bool) and isinstance(rep["caveats"], str)
for e in rep["events"]:
    assert set(e.keys()) == {"onset", "end"}
print("report.json schema OK; events:", rep["events"])
print("files:", os.path.getsize("output/mhw_mask.nc"), os.path.getsize("output/report.json"))
print("ALL CHECKS PASSED")
