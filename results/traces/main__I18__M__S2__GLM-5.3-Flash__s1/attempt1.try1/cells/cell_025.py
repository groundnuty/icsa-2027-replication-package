import os, json
import numpy as np
import xarray as xr

hot = np.load("/tmp/hot.npy")          # (92,60,60) bool, verified equal to fresh recompute
sea = np.load("/tmp/sea.npy")          # (60,60) bool
T = hot.shape[0]
hot_cells = hot.reshape(T, -1)[:, sea.reshape(-1)]
nsea = hot_cells.shape[1]

def detect_A_list(seq):
    """runs of >=5 hot days are MHWs; then MHWs separated by 1-2 non-hot days are joined; gap days belong."""
    seq = list(seq); L = len(seq)
    runs = []; t = 0
    while t < L:
        if seq[t]:
            u = t
            while u + 1 < L and seq[u+1]: u += 1
            runs.append([t, u]); t = u + 1
        else:
            t += 1
    mhw_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
    merged = []
    for r in mhw_runs:
        if merged and r[0] - merged[-1][1] - 1 <= 2:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    out = np.zeros(L, bool)
    for s, e in merged: out[s:e+1] = True
    return out, merged

def detect_A_indep(seq):
    """Independent rewrite (vectorized boundaries)."""
    seq = np.asarray(seq, bool); L = len(seq)
    d = np.diff(np.concatenate([[0], seq.view(np.int8), [0]]))
    starts = np.flatnonzero(d == 1); ends = np.flatnonzero(d == -1) - 1
    keep = (ends - starts + 1) >= 5
    starts, ends = starts[keep], ends[keep]
    out = np.zeros(L, bool)
    if len(starts):
        cs, ce = starts[0], ends[0]
        for s, e in zip(starts[1:], ends[1:]):
            if s - ce <= 3:
                ce = e
            else:
                out[cs:ce+1] = True; cs, ce = s, e
        out[cs:ce+1] = True
    return out

mhw_cells = np.zeros((T, nsea), bool)
n_cell_events = 0
for n in range(nsea):
    a, merged = detect_A_list(hot_cells[:, n])
    assert np.array_equal(a, detect_A_indep(hot_cells[:, n])), n
    mhw_cells[:, n] = a
    n_cell_events += len(merged)
active = mhw_cells.any(axis=1)
print("per-cell MHW events over all cells:", n_cell_events)
print("mhw sea-cell-days:", int(mhw_cells.sum()), "of", T*nsea)
print("active days:", int(active.sum()), "of", T)
print("active:", "".join("1" if x else "0" for x in active))
assert np.array_equal(mhw_cells, np.load("/tmp/mhw_final.npy"))
assert np.array_equal(active, np.load("/tmp/active_final.npy"))
print("matches earlier final computation")

# regional events
EPOCH = np.datetime64("1970-01-01")
tdates = EPOCH + np.load("/tmp/tgt_times.npy").astype("timedelta64[D]")
tstr = tdates.astype(str)
idx = np.flatnonzero(active)
evs = []
s = idx[0]; prev = idx[0]
for i in idx[1:]:
    if i != prev + 1:
        evs.append((s, prev)); s = i
    prev = i
evs.append((s, prev))
events = [{"onset": str(tstr[a]), "end": str(tstr[b])} for a, b in evs]
print("events:", json.dumps(events))

# ---- write mhw_mask.nc ----
mhw_full = np.zeros((T, 60, 60), np.uint8)
mhw_full.reshape(T, -1)[:, sea.reshape(-1)] = mhw_cells.astype(np.uint8)
assert int(mhw_full.sum()) == int(mhw_cells.sum())

lat_out = np.load("/tmp/latlon.npy")[:60].astype(np.float32)
lon_out = np.load("/tmp/latlon.npy")[60:].astype(np.float32)

ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_full)},
    coords={"time": tdates, "lat": lat_out, "lon": lon_out},
)
ds_out["mhw"].attrs.update({"long_name": "per-cell marine heatwave mask", "flag_values": np.array([0, 1], np.uint8),
                            "flag_meanings": "not_in_mhw in_mhw"})
enc = {"mhw": {"dtype": "uint8", "_FillValue": None},
       "time": {"dtype": "int32", "units": "days since 1970-01-01", "calendar": "proleptic_gregorian"}}
ds_out.to_netcdf("output/mhw_mask.nc", engine="h5netcdf", encoding=enc)
print("wrote output/mhw_mask.nc")

report = {
    "region": {"lat_min": 57.13, "lat_max": 58.33, "lon_min": 22.79, "lon_max": 23.99},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2010-06-01", "end": "2010-08-31"},
    "events": events,
    "complete": True,
    "caveats": ("All 4018 baseline days (1992-01-01 to 2002-12-31) were read; per the +/5-day pool windows the "
                "climatology/threshold additionally read 1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05. "
                "The climatology was computed as specified but is not used in the mask. 299 of 3600 region cells "
                "are land (SST NaN on every day) and are 0 in the mask; the 3301 sea cells have finite SST on every "
                "target day. Source SST is stored float32 (0.01 K steps); all statistics in float64. Hot-day test: "
                "stored kelvin SST >= smoothed threshold. Per-cell joining follows the spec sentence order: runs of "
                ">=5 consecutive hot days are MHWs first, then MHWs separated by 1-2 non-hot days are joined, gap "
                "days included. The regional active days, and hence the reported event, are identical under the "
                "alternative join order (join all hot runs first, keep those >=5 days)."),
}
with open("output/report.json", "w") as fh:
    json.dump(report, fh, indent=2)
print("wrote output/report.json")
