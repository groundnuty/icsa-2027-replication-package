import numpy as np, pandas as pd, json, os

z = np.load("work/data.npz")
targ = z["targ"].astype(np.float64)
targ_dates = pd.DatetimeIndex(z["targ_dates"].astype(str))
latv, lonv = z["lat"], z["lon"]
c = np.load("work/clim.npz")
thr_s = c["thr_s"]; clm_s = c["clm_s"]; targ_doy = c["targ_doy"]

nt, nlat, nlon = targ.shape
# sea cells: finite on every target day
sea = np.isfinite(targ).all(axis=0)
print("sea cells:", sea.sum(), "of", nlat*nlon)

# thresholds aligned to target doys: thr_s[d-1] for d = targ_doy
thr_t = thr_s[targ_doy - 1]            # (92, 60, 60)
clm_t = clm_s[targ_doy - 1]
print("thresholds finite on all target days for sea cells:",
      np.isfinite(thr_t[:, sea]).all())

hot = np.zeros((nt, nlat, nlon), dtype=bool)
hot[:, sea] = targ[:, sea] >= thr_t[:, sea]     # float64 comparison, kelvin as stored
print("hot cell-days:", hot.sum(), "of", int(hot[:, sea].sum()) , "possible sea cell-days:", nt*int(sea.sum()))

def runs_1d(h):
    """maximal True runs as (start, end) inclusive indices"""
    out = []
    n = len(h)
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j + 1 < n and h[j+1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out

def merge_events(events, max_gap):
    """merge consecutive (start,end) events separated by <= max_gap non-event days"""
    if not events: return []
    evs = [list(events[0])]
    for s, e in events[1:]:
        if s - evs[-1][1] - 1 <= max_gap:
            evs[-1][1] = e
        else:
            evs.append([s, e])
    return [tuple(x) for x in evs]

def detect_variantA(h, min_run=5, max_gap=2):
    """MHW = hot runs >=5; then join MHWs separated by 1-2 non-hot days"""
    evs = []
    for r in runs_1d(h):
        if r[1] - r[0] + 1 >= min_run:
            evs.append(r)
    return merge_events(evs, max_gap)

def detect_variantB(h, min_run=5, max_gap=2):
    """join all hot runs separated by 1-2 gaps first, then keep events >=5 days"""
    evs = merge_events(runs_1d(h), max_gap)
    return [e for e in evs if e[1] - e[0] + 1 >= min_run]

maskA = np.zeros((nt, nlat, nlon), dtype=np.uint8)
maskB = np.zeros((nt, nlat, nlon), dtype=np.uint8)
n_evA = n_evB = 0
lensA = []
for i in range(nlat):
    for j in range(nlon):
        if not sea[i, j]:
            continue
        h = hot[:, i, j]
        eA = detect_variantA(h); eB = detect_variantB(h)
        n_evA += len(eA); n_evB += len(eB)
        for s, e in eA:
            maskA[s:e+1, i, j] = 1
            lensA.append(e - s + 1)
        for s, e in eB:
            maskB[s:e+1, i, j] = 1
print("variant A: per-cell MHWs:", n_evA, "variant B:", n_evB)
print("masks identical:", np.array_equal(maskA, maskB))
print("variant A mask cell-days:", int(maskA.sum()))
lensA = np.array(lensA)
print("per-cell MHW lengths: min", lensA.min(), "max", lensA.max(), "mean", round(lensA.mean(),2), "median", np.median(lensA))
# how many cells have >=1 MHW
cells_with = (maskA.sum(axis=0) > 0)
print("cells with >=1 per-cell MHW:", cells_with.sum(), "of", int(sea.sum()))
np.save("work/maskA.npy", maskA); np.save("work/maskB.npy", maskB); np.save("work/sea.npy", sea)
print("per-day active cells (variant A):", [int(maskA[d].sum()) for d in range(nt)])
