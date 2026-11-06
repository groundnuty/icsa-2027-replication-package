import numpy as np, h5py
from datetime import date, timedelta
import pickle

sst_t = np.load("/work/sst_target.npy")       # (92, 60, 60) float64
thr_s = np.load("/work/thr_smooth.npy")       # (366, 60, 60) float64
with open("/work/window_dates.pkl","rb") as f:
    wd = pickle.load(f)
lat_idx, lon_idx = wd["lat_idx"], wd["lon_idx"]
i0, i1 = lat_idx[0], lat_idx[-1]+1
j0, j1 = lon_idx[0], lon_idx[-1]+1

with h5py.File("/data/icsa2027_data_20261101T090944Z/s1z/sst_19920601.nc","r") as f:
    lat = f["latitude"][:].astype(np.float64)
    lon = f["longitude"][:].astype(np.float64)
lat_reg = lat[i0:i1]; lon_reg = lon[j0:j1]

MD_CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
target_dates = []
d = date(2012,6,1)
while d <= date(2012,8,31):
    target_dates.append(d); d += timedelta(days=1)
doys = np.array([MD_CUM[t.month-1] + t.day for t in target_dates])  # (92,)
print("target doys:", doys[0], "..", doys[-1])

# --- 1. sea cells: SST finite on EVERY day of target period ---
sea_mask = np.isfinite(sst_t).all(axis=0)   # (60,60) bool
print("sea cells:", sea_mask.sum(), "of", 60*60, " land(non-sea):", (~sea_mask).sum())

# --- 3. hot days (restricted to target period) ---
thr_target = thr_s[doys - 1]                # (92, 60, 60)
with np.errstate(invalid="ignore"):
    hot = (sst_t >= thr_target) & sea_mask[None, :, :]
print("hot days total:", hot.sum(), "of", hot.size)
print("hot frac among sea cells:", hot.sum() / sea_mask.sum() / 92.0)

# --- per-cell MHW runs with >=5 consecutive hot days, join gaps of 1-2 days ---
def mhw_mask_1d(hot_series):
    """hot_series: 1-D bool over target days. Returns bool mask of MHW days."""
    n = len(hot_series)
    mask = np.zeros(n, dtype=bool)
    i = 0
    while i < n:
        if hot_series[i]:
            j = i
            while j < n and hot_series[j]:
                j += 1
            runlen = j - i
            gap = 0
            k = j
            while k < n and not hot_series[k]:
                gap += 1; k += 1
            # can we join to next run? if gap <= 2 AND (runlen + gap + nextrunlen >= 5)? 
            # Rule: runs of >=5 hot days are MHWs; MHWs separated by 1-2 non-hot days are joined.
            # Interpretation A: extend run across gap if (runlen >= 5 OR already joined) and gap<=2 and combined >=5
            # The published catalogue joins gaps between per-cell MHWs (both runs >= 5)
            if runlen >= 5:
                # look ahead: next hot run after the gap
                if gap <= 2 and k < n:
                    # combined run candidate: runlen + gap + nextrunlen
                    # find next run length
                    k2 = k
                    while k2 < n and hot_series[k2]:
                        k2 += 1
                    nextrun = k2 - k
                    if runlen + gap + nextrun >= 5:
                        # join if both runs are MHWs (>=5) OR combined >=5 - since both runs >=5 given runlen>=5 and nextrun>=5? 
                        # nextrun could be < 5 only if it ends at array end; but then it's not an MHW alone
                        pass
                # simple approach: mark the run; joining handled below
            i = j
        else:
            i += 1
    return mask

# Simpler robust implementation: 
def mhw_mask(hot_series, min_run=5, max_gap=2):
    n = len(hot_series)
    mask = np.zeros(n, dtype=bool)
    # find all maximal runs
    runs = []
    i = 0
    while i < n:
        if hot_series[i]:
            j = i
            while j < n and hot_series[j]:
                j += 1
            runs.append([i, j-1])  # inclusive
            i = j
        else:
            i += 1
    # merge runs separated by gap <= max_gap IF the merged run has length >= min_run
    # but merging is between MHWs (runs >= 5). So: keep only runs >= min_run first,
    # then join those separated by <=2 days, then all days in joined event belong to it.
    mhw_runs = [r for r in runs if r[1] - r[0] + 1 >= min_run]
    # join
    merged = []
    for r in mhw_runs:
        if merged and r[0] - merged[-1][1] - 1 <= max_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    for a, b in merged:
        mask[a:b+1] = True
    return mask, merged

# test on a couple of cells
for (ii, jj) in [(10,10), (30,30), (0,0), (59,59)]:
    if not sea_mask[ii, jj]: 
        continue
    m, runs = mhw_mask(hot[:, ii, jj])
    print(f"cell({ii},{jj}) lat={lat_reg[ii]:.2f} lon={lon_reg[jj]:.2f} mhw days:", m.sum(), "runs:", runs)
