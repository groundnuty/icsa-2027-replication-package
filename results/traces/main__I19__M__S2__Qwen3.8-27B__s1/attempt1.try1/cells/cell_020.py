script = r'''
import numpy as np
import xarray as xr
import pandas as pd
from datetime import date, timedelta

PATH = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
z = np.load('/work/interim.npz')
thr = z['thr']; clim = z['clim']
rlat = z['rlat']; rlon = z['rlon']
tgt = z['tgt']; tgt_dates = z['tgt_dates'].astype(str)
base_dates = z['base_dates'].astype(str)
ncells = 3600

# ---------- independent verification of one pool (cell 0, doy 153 = Jun 1) ----------
ds = xr.open_dataset(PATH, engine="h5netcdf")
lat_all = ds.latitude.values.astype(np.float64); lon_all = ds.longitude.values.astype(np.float64)
tol = 1e-6
li = np.where((lat_all >= 57.13-tol) & (lat_all <= 58.33+tol))[0][0]
lo = np.where((lon_all >= 22.79-tol) & (lon_all <= 23.99+tol))[0][0]
t = pd.to_datetime(ds.time.values)
def val_on(dsdate):
    i = int(np.searchsorted(ds.time.values, np.datetime64(dsdate)))
    return float(ds.analysed_sst[i, li, lo].values)
pool = []
for Y in range(1992, 2003):
    b = date(Y, 6, 1)
    for k in range(-5, 6):
        d = b + timedelta(days=k)
        pool.append(val_on(f"{d.year:04d}-{d.month:02d}-{d.day:02d}"))
pool = np.array(pool)
n = int(np.isfinite(pool).sum())
h1 = n*0.9 + 0.5
h1 = min(max(h1, 1.0), float(n))
lo_i = int(np.floor(h1)); frac = h1 - lo_i
xs = np.sort(pool[np.isfinite(pool)])
if lo_i >= n:
    q_manual = xs[-1]
else:
    q_manual = xs[lo_i-1] + frac*(xs[lo_i]-xs[lo_i-1])
print("cell0 doy153: finite n =", n, " manual hazen =", q_manual, " pipeline thr =", thr[152, 0],
      " match:", np.isclose(q_manual, thr[152,0]))
print("mean check:", np.nanmean(pool), clim[152,0], np.isclose(np.nanmean(pool), clim[152,0]))
ds.close()

# ---------- fixed smoothing: centred 31-day wrap ----------
off = np.arange(-15, 16)
idxm = (np.arange(366)[:,None] + off[None,:]) % 366   # (366,31)
# pure advanced indexing on axis 0: thr[idxm] -> (366, 31, 3600)
thr_s = thr[idxm].mean(axis=1)    # (366, 3600)
clim_s = clim[idxm].mean(axis=1)
print("shapes:", thr_s.shape, clim_s.shape)
# verify wrap: day 1 window = days 352..366 and 1..15
i = 0
expect = np.concatenate([thr[351:366], thr[0:15]]).mean()
print("wrap check day1:", thr_s[0,0], expect, np.isclose(thr_s[0,0], expect))
# verify a middle day: day 100 -> 85..114
expect2 = thr[84:115].mean()
print("mid check day100:", thr_s[99,0], expect2, np.isclose(thr_s[99,0], expect2))
np.savez_compressed('/work/smooth.npz', thr_s=thr_s, clim_s=clim_s)

# ---------- sea cells ----------
sea = np.isfinite(tgt).all(axis=0)          # (3600,)
print("sea cells:", sea.sum(), "of", ncells)

# ---------- hot days ----------
def doy_of(m, d):
    cum = [0,31,60,91,121,152,182,213,244,274,305,335]
    return cum[m-1] + d
doy_t = np.array([doy_of(int(s[5:7]), int(s[8:10])) for s in tgt_dates])
print("target doys:", doy_t[0], "..", doy_t[-1])
hot = np.zeros(tgt.shape, dtype=bool)
for i in range(tgt.shape[0]):
    hot[i] = tgt[i] >= thr_s[doy_t[i]-1]
hot &= sea[None, :, :]
print("total hot cell-days:", hot.sum())

# ---------- per-cell runs, >=5 days, merge gaps 1-2 ----------
nt = tgt.shape[0]
mem = np.zeros((nt, ncells), dtype=bool)
for c in range(ncells):
    h = hot[:, c]
    if not h.any():
        continue
    # find runs of 1s
    dh = np.diff(np.concatenate(([0], h.view(np.int8), [0])))
    starts = np.where(dh == 1)[0]
    ends   = np.where(dh == -1)[0]   # exclusive
    keep = ends - starts >= 5
    if not keep.any():
        continue
    starts = starts[keep]; ends = ends[keep]
    # greedy merge: gap between end of current and start of next in {1,2}
    merged_s = [starts[0]]; merged_e = [ends[0]]
    for s, e in zip(starts[1:], ends[1:]):
        gap = s - merged_e[-1]
        if gap in (1, 2):
            merged_e[-1] = e
        else:
            merged_s.append(s); merged_e.append(e)
    for s, e in zip(merged_s, merged_e):
        mem[s:e, c] = True
print("mask cell-days in MHW:", mem.sum())

# ---------- regional events ----------
active = mem.any(axis=1)
ev = []
i = 0
while i < nt:
    if active[i]:
        j = i
        while j+1 < nt and active[j+1]:
            j += 1
        ev.append((str(tgt_dates[i]), str(tgt_dates[j])))
        i = j+1
    else:
        i += 1
print("events:", ev)
np.savez_compressed('/work/mhw.npz', mem=mem, active=active, tgt_dates=tgt_dates,
                    tgt=tgt, thr_s=thr_s, sea=sea)
'''
with open('/work/pipeline2.py','w') as f:
    f.write(script)
print("written")
