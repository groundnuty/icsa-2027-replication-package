import numpy as np, xarray as xr, json, os

z = np.load('/work/interim.npz'); tc = np.load('/work/thr_clim.npz')
sst_t, sea, li, oi, latv, lonv = z['sst_t'], z['sea'], z['li'], z['oi'], z['lat'], z['lon']
thr_s = tc['thr_s']
NC = 3600
i0 = int(z['t_i0']); i1 = int(z['t_i1'])
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t = ds.time.values
nt = i1 - i0
assert nt == 92

def md_to_doy(m, dd):
    if (m, dd) == (2, 29): return 60
    days = [31,28,31,30,31,30,31,31,30,31,30,31]
    cum = 0
    for mm in range(1, m): cum += days[mm-1]
    doy = cum + dd
    if m > 2: doy += 1
    return doy

doys = np.array([md_to_doy(int((t[i0+k] - t[i0+k].astype('datetime64[Y]')).astype('timedelta64[D]')//np.timedelta64(1,'D')) % 32 + (int((t[i0+k] - t[i0+k].astype('datetime64[Y]')).astype('timedelta64[D]')//np.timedelta64(1,'D')) // 32 + 1) if False else 0, 0) for k in range(nt)]) if False else None
# simpler: derive month/day from datetime64
import pandas as pd
tdates = pd.to_datetime(t[i0:i1])
doys = np.array([md_to_doy(int(d.month), int(d.day)) for d in tdates])
print("target doys:", doys[0], "..", doys[-1], " unique count:", len(set(doys.tolist())))
assert doys[0] == 153 and doys[-1] == 244 and len(set(doys.tolist())) == 92

# hot mask
hot = np.zeros((nt, 60, 60), bool)
with np.errstate(invalid='ignore'):
    hot = sst_t >= thr_s[doys-1][:, None, None]
hot = hot & sea[None, :, :]
# NaN comparisons are False; double check no NaN sst in target (sea cells finite by definition)
assert np.all(np.isfinite(sst_t[sea]))

hot2 = hot.reshape(nt, NC)

def cell_mhw_intervals(h):
    # h: (nt,) bool; return list of merged MHW intervals (start, end) inclusive
    n = len(h)
    runs = []
    i = 0
    while i < n:
        if h[i]:
            j = i
            while j + 1 < n and h[j+1]: j += 1
            if j - i + 1 >= 5:
                runs.append([i, j])
            i = j + 1
        else:
            i += 1
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return merged

mask2 = np.zeros((nt, NC), bool)
n_mhw_cells = 0
total_runs = 0
for c in range(NC):
    if not sea.reshape(NC)[c]: continue
    ivs = cell_mhw_intervals(hot2[:, c])
    if ivs:
        n_mhw_cells += 1
        total_runs += len(ivs)
    for s, e in ivs:
        mask2[s:e+1, c] = True

mask = mask2.reshape(nt, 60, 60).astype(np.uint8)
print("cells with >=1 per-cell MHW:", n_mhw_cells, "| total per-cell MHWs:", total_runs)

active = mask2.any(axis=1)
events = []
i = 0
while i < nt:
    if active[i]:
        j = i
        while j + 1 < nt and active[j+1]: j += 1
        events.append((str(tdates[i].date()), str(tdates[j].date())))
        i = j + 1
    else:
        i += 1
print("active days:", int(active.sum()), "of", nt)
print("regional events:", events)

# store for output step
np.savez_compressed('/work/mhw.npz', mask=mask, events=np.array(events, dtype=object), active=active)
print("saved mhw mask")
