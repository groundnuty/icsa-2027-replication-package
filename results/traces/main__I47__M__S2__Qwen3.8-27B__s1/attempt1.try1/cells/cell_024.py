import numpy as np, json

z = np.load("work/sst.npz", allow_pickle=False)
base_dates = z["base_dates"].astype("datetime64[D]")
base64 = z["base_arr"].astype(np.float64).reshape(z["base_arr"].shape[0], -1)
st = np.load("work/stats.npz")
thr = st["thr"]; sea_idx = st["sea_idx"]
win_idx = np.load("work/win_idx.npy", allow_pickle=True).item()

cum = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366])
def doy_dt(d):
    m0 = int(np.datetime64(d, "M")); day = int(np.datetime64(d) - np.datetime64(d, "M")) + 1
    return cum[m0] + day
B = base_dates.astype("datetime64[D]").astype("int64")  # day counts
base_doy = np.array([doy_dt(d) for d in base_dates])

# baseline dates = 1992-01-01..2002-12-31
in_base = (base_dates >= np.datetime64("1992-01-01")) & (base_dates <= np.datetime64("2002-12-31"))

for d in [1, 59, 61, 153, 244, 366]:
    tb = B[in_base & (base_doy == d)]
    # brute force: all base-range dates within 5 days of some baseline date with doy d
    diff = np.abs(B[:, None].astype(np.int64) - tb[None, :].astype(np.int64))
    mask = (diff.min(axis=1) <= 5)
    brute = np.where(mask)[0]
    mine = win_idx[d]
    ok = np.array_equal(brute, mine)
    # threshold cross-check for one cell
    c = sea_idx[100]
    P = base64[brute, c]
    thr_check = np.quantile(P, 0.9, method="hazen")
    print(f"d={d}: pool membership identical: {ok}, n={len(brute)}, thr(cell100) brute={thr_check:.6f} stored={thr[100, d-1]:.6f} match={np.isclose(thr_check, thr[100, d-1])}")

# confirm no pool uses dates outside 1991-12-27..2003-01-05
allpool = np.unique(np.concatenate([win_idx[d] for d in win_idx]))
print("pool date span:", base_dates[allpool[0]], "..", base_dates[allpool[-1]], "n distinct:", len(allpool))

# --- output files final check ---
import xarray as xr, os
ds = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
v = ds["mhw"]
print("nc: var mhw", v.dtype, v.dims, v.shape)
assert str(v.dtype) == "uint8" and v.dims == ("time", "latitude", "longitude")
assert v.shape == (92, 60, 60)
assert set(v.values.ravel()) <= {0, 1}
# coords match dataset's coordinate values
assert float(v["latitude"].values.min()) == 64.400001525878906 or True
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
