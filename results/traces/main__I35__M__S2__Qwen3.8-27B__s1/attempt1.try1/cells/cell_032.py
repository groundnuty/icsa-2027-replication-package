import numpy as np, json
import xarray as xr

# ---- validate mhw_mask.nc ----
chk = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print(chk)
m = chk["mhw"]
assert m.dims == ("time", "lat", "lon"), m.dims
assert m.dtype == np.uint8, m.dtype
assert m.shape == (92, 60, 60)
tv = chk.time.values
assert str(tv[0])[:10] == "2009-06-01" and str(tv[-1])[:10] == "2009-08-31"
lv, ov = chk.lat.values, chk.lon.values
assert np.all(lv >= 59.93) and np.all(lv <= 61.13) and np.all(ov >= 18.69) and np.all(ov <= 19.89)
vals = m.values
assert set(np.unique(vals)) <= {0, 1}
print("mhw unique values:", np.unique(vals).tolist(), " total ones:", int(vals.sum()))

# ---- validate report.json ----
rep = json.load(open("output/report.json"))
assert set(rep.keys()) == {"region", "baseline_analysed", "target_analysed", "events", "complete", "caveats"}
assert set(rep["region"].keys()) == {"lat_min", "lat_max", "lon_min", "lon_max"}
assert rep["region"] == {"lat_min": 59.93, "lat_max": 61.13, "lon_min": 18.69, "lon_max": 19.89}
assert rep["baseline_analysed"] == {"start": "1992-01-01", "end": "2002-12-31"}
assert rep["target_analysed"] == {"start": "2009-06-01", "end": "2009-08-31"}
for e in rep["events"]:
    assert set(e.keys()) == {"onset", "end"}
assert rep["complete"] is True
assert isinstance(rep["caveats"], str)
print("report.json OK:", json.dumps(rep["events"]))

# ---- cross-check mask vs flat array & independent single-cell recompute ----
sea = np.load("/tmp/sea.npy")
mhw_flat = np.load("/tmp/final_mhw.npy")
li, oi = np.where(sea)
recon = np.zeros((92, 60, 60), np.uint8)
recon[:, li, oi] = mhw_flat
assert np.array_equal(recon, vals)
assert (vals[:, ~sea].astype(bool)).sum() == 0   # land cells all 0
print("mask consistent with per-cell results; land cells all 0")

# independent recompute for one cell: pick a cell inside event 1 with many MHW days
c = int(np.argmax(mhw_flat.sum(axis=0)))
print("busiest flat cell:", c, "-> lat", lv[li[c]], "lon", ov[oi[c]], "MHW days:", int(mhw_flat[:, c].sum()))
X = np.load("/tmp/X.npy"); p3 = np.load("/tmp/p3.npy"); M = np.load("/tmp/M.npy")
PREF = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy(dates):
    dates = dates.astype("datetime64[D]")
    d = dates.astype("int64")
    first = dates.astype("datetime64[M]").astype("datetime64[D]").astype("int64")
    month = dates.astype("datetime64[M]").astype("int64") % 12
    return PREF[month] + d - first + 1
def hazen(x, p=0.9):
    x = np.sort(x); n = len(x); pos = n*p - 0.5
    i = int(np.floor(pos)); f = pos - i
    return x[-1] if i >= n-1 else x[i] + f*(x[i+1]-x[i])
j = int(c)
col = X[:, li[c]//60*60 + (j)]  # placeholder; do it properly below:
# flatten index -> (lat, lon): c is index into C-order ravel of sea mask
row, colxy = divmod(c, 60)
raw = np.full(366, np.nan)
for d in range(1, 367):
    if d == 60: continue
    v = X[M[d-1], row, colxy]
    v = v[np.isfinite(v)]
    raw[d-1] = hazen(v)
raw[59] = (raw[58] + raw[60]) / 2
raw_s = np.array([raw[(dd-15+np.arange(31)) % 366].mean() for dd in range(366)])
tdates = np.datetime64("2009-06-01") + np.arange(92)
tdoy = doy(tdates)
SSTc = p3[:, row, colxy]
hotc = SSTc >= raw_s[tdoy-1]
# manual run detection (naive)
runs = []
i = 0
while i < 92:
    if hotc[i]:
        j2 = i
        while j2+1 < 92 and hotc[j2+1]: j2 += 1
        if j2-i+1 >= 5: runs.append([i, j2])
        i = j2+1
    else: i += 1
merged = []
for s, e in runs:
    if merged and s - merged[-1][1] - 1 <= 2: merged[-1][1] = e
    else: merged.append([s, e])
ind = np.zeros(92, bool)
for s, e in merged: ind[s:e+1] = True
assert np.array_equal(ind.astype(np.uint8), mhw_flat[:, c])
print("independent single-cell recompute matches: PASS (MHW days %d, runs %s)" % (int(ind.sum()), merged))
print("ALL VALIDATIONS PASSED")
