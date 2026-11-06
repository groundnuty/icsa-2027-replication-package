import numpy as np, xarray as xr, json, os

ds = xr.open_dataset("/work/output/mhw_mask.nc", engine="h5netcdf")
print(ds)
m = ds["mhw"]
print("dtype:", m.dtype, "| dims:", m.dims, "| shape:", m.shape)
print("mhw unique:", np.unique(m.values))
print("sum:", int(m.values.sum()))

# coordinate values must match the dataset exactly
src = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc", engine="h5netcdf")
assert np.array_equal(ds.lat.values, src.latitude.values[218:278])
assert np.array_equal(ds.lon.values, src.longitude.values[601:661])
print("lat/lon match dataset values: True")
print("time first/last:", str(ds.time.values[0])[:10], str(ds.time.values[-1])[:10], "n =", ds.time.size)
print("time[0] equals source time[0]:", ds.time.values[0] == src.time.values[0])

# independent recheck: mask == 1 exactly where per-cell MHW (from saved arrays)
mhw = np.load("/work/mhw_mask.npy")
print("mask content matches computed mask:", np.array_equal(m.values, mhw))

# spot check one cell: print SST vs threshold across the first event for one MHW cell
import h5py
thr_s = np.load("/work/thr_s.npy")
tf = np.load("/work/target_finite.npy")
# choose cell with the longest MHW
import datetime as dt
runs = []
T = 92
# find a cell with a long run from mhw
best = None
for r in range(60):
    for c in range(60):
        col = mhw[:, r, c]
        if col.sum() > 0:
            # longest run
            s = None
            for k in range(T):
                if col[k] and s is None: s = k
                if (not col[k] or k == T-1) and s is not None:
                    e = k if col[k] else k-1
                    if best is None or (e-s+1) > best[0]: best = (e-s+1, r, c, s, e)
                    s = None
L, r, c, s, e = best
print("longest per-cell MHW: %d days, cell (lat %.2f, lon %.2f), %s..%s" % (
    L, ds.lat.values[r], ds.lon.values[c], str(ds.time.values[s])[:10], str(ds.time.values[e])[:10]))
sst_days = []
start = dt.date(1991,12,27)
for k in range(s-1, e+2):
    d = start + dt.timedelta(days=(dt.date(2013,6,1)-start).days + k)
    with h5py.File("/data/icsa2027_data_20261101T090944Z/s1z/sst_"+d.strftime("%Y%m%d")+".nc","r") as f:
        v = f["analysed_sst"][0, 218+r, 601+c]
    dy = d.timetuple().tm_yday
    sst_days.append((str(d), float(v) if np.isfinite(v) else float('nan'), float(thr_s[dy-1, r, c])))
for row in sst_days:
    print("  %s SST=%.3f thr=%.3f %s" % (row[0], row[1], row[2], "HOT" if row[1] >= row[2] else "-"))

rep = json.load(open("/work/output/report.json"))
print("report keys:", sorted(rep.keys()))
assert set(rep.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}
print("report fields OK; complete:", rep["complete"], "| events:", rep["events"])
print("\nfiles:", os.listdir("/work/output"))
print("sizes:", {f: os.path.getsize("/work/output/"+f) for f in os.listdir("/work/output")})
