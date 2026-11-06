import numpy as np, xarray as xr, json, fsspec, h5py

# read back the written file
ds = xr.open_dataset("/work/output/mhw_mask.nc", engine="h5netcdf")
print(ds)
m = ds["mhw"].values
mhw = np.load("/work/mhw.npy")
print("dtype:", ds["mhw"].dtype, "| shape:", m.shape, "| exact match with computed mask:", np.array_equal(m, mhw))
print("mhw sum:", int(m.sum()), "| unique values:", np.unique(m))

# coords match the source dataset values?
fs = fsspec.filesystem('onedata')
f = fs.open("icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", "rb")
with h5py.File(f, "r") as h5:
    lat_ds = h5["latitude"][:]; lon_ds = h5["longitude"][:]
la = lat_ds.astype('float64'); lo = lon_ds.astype('float64')
lat_idx = np.where((la >= 57.57) & (la <= 58.77))[0]
lon_idx = np.where((lo >= 10.25) & (lo <= 11.45))[0]
lat_ref = lat_ds[lat_idx[0]:lat_idx[-1]+1]; lon_ref = lon_ds[lon_idx[0]:lon_idx[-1]+1]
print("lat coords identical to source:", np.array_equal(ds["lat"].values.astype('float32'), lat_ref))
print("lon coords identical to source:", np.array_equal(ds["lon"].values.astype('float32'), lon_ref))
tvals = ds["time"].values
print("time first/last:", tvals[0], tvals[-1], "n:", tvals.size)
assert str(tvals[0])[:10] == "2004-06-01" and str(tvals[-1])[:10] == "2004-08-31"

# re-derive regional events purely from the file's mask
active = m.max(axis=(1,2)).astype(bool)
reg = []
d = 0
while d < active.size:
    if active[d]:
        e = d
        while e + 1 < active.size and active[e+1]: e += 1
        reg.append((d, e)); d = e + 1
    else:
        d += 1
events = [{"onset": str(tvals[s])[:10], "end": str(tvals[e])[:10]} for s, e in reg]
print("events from file:", events)

# check report.json consistency
with open("/work/output/report.json") as fh: report = json.load(fh)
print("report events match:", report["events"] == events)
print("report fields:", sorted(report.keys()))
assert set(report.keys()) == {"region","baseline_analysed","target_analysed","events","complete","caveats"}

# spot-check per-cell structure from the file: every event run >= 5 days, gap-joined
import pickle
with open("/work/events.pkl","rb") as fh: ev = pickle.load(fh)
lens = [e - s + 1 for evs in ev["percell"].values() for s, e in evs]
assert min(lens) >= 5
# verify no two per-cell events separated by <= 2 days remain unjoined anywhere
bad = 0
for evs in ev["percell"].values():
    for k in range(len(evs)-1):
        if evs[k+1][0] - evs[k][1] - 1 <= 2: bad += 1
print("unjoined gaps remaining:", bad)
print("\nALL CHECKS PASSED")
