import numpy as np

sea = np.load("/tmp/sea.npy")
li, oi = np.where(sea)
mhw_flat = np.load("/tmp/final_mhw.npy")
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

def independent_cell_mask(c):
    row, colxy = int(li[c]), int(oi[c])
    assert int(sea[row, colxy]) == 1
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
    return ind, merged

c = int(np.argmax(mhw_flat.sum(axis=0)))
ind, merged = independent_cell_mask(c)
assert np.array_equal(ind.astype(np.uint8), mhw_flat[:, c])
print("busiest cell %d (grid %d,%d): independent recompute matches; MHW days %d, runs %s"
      % (c, li[c], oi[c], int(ind.sum()), merged))

rng = np.random.default_rng(42)
for c2 in rng.integers(0, mhw_flat.shape[1], 10):
    ind2, _ = independent_cell_mask(int(c2))
    assert np.array_equal(ind2.astype(np.uint8), mhw_flat[:, c2]), int(c2)
print("10 random spot cells: all match -> PASS")

# also verify the mask in the written nc file one more time, end-to-end
import xarray as xr
chk = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
m = chk.mhw.values
li3, oi3 = np.where(sea)
recon = np.zeros((92, 60, 60), np.uint8)
recon[:, li3, oi3] = mhw_flat
assert np.array_equal(recon, m)
print("output/mhw_mask.nc consistent: PASS")
