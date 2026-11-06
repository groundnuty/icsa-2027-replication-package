import numpy as np, xarray as xr, json, os, pandas as pd

z = np.load('/work/interim.npz'); tc = np.load('/work/thr_clim.npz')
sst_t, sea, li, oi = z['sst_t'], z['sea'], z['li'], z['oi']
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

tdates = pd.to_datetime(t[i0:i1])
doys = np.array([md_to_doy(int(d.month), int(d.day)) for d in tdates])
assert doys[0] == 153 and doys[-1] == 244 and len(set(doys.tolist())) == 92
assert np.all(np.isfinite(sst_t[:, sea]))

hot = (sst_t >= thr_s[doys-1]) & sea[None, :, :]   # (92,60,60)

hot2 = hot.reshape(nt, NC)

def cell_mhw_intervals(h):
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
durs = []
for c in range(NC):
    if not sea.reshape(NC)[c]: continue
    ivs = cell_mhw_intervals(hot2[:, c])
    if ivs:
        n_mhw_cells += 1
        total_runs += len(ivs)
        for s, e in ivs:
            durs.append(e - s + 1)
            mask2[s:e+1, c] = True

mask = mask2.reshape(nt, 60, 60).astype(np.uint8)
print("cells with >=1 per-cell MHW:", n_mhw_cells, "| total per-cell MHWs:", total_runs,
      "| duration min/max:", min(durs), max(durs))

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

np.savez_compressed('/work/mhw.npz', mask=mask, events=np.array(events, dtype=object), active=active,
                    n_mhw_cells=n_mhw_cells, total_runs=total_runs)
print("saved mhw mask")
