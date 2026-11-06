script = '''
import numpy as np
import xarray as xr
import pandas as pd
from datetime import date, timedelta

PATH = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
z = np.load('/work/interim.npz', allow_pickle=True)
thr = z['thr']; clim = z['clim']
rlat = z['rlat']; rlon = z['rlon']
tgt = z['tgt']
tgt_dates = np.asarray(z['tgt_dates'], dtype=str)
base_dates = np.asarray(z['base_dates'], dtype=str)
ncells = 3600

# ---------- independent verification (single cell, doy 153 = Jun 1) ----------
ds = xr.open_dataset(PATH, engine="h5netcdf")
lat_all = ds.latitude.values.astype(np.float64); lon_all = ds.longitude.values.astype(np.float64)
tol = 1e-6
li0 = np.where((lat_all >= 57.13-tol) & (lat_all <= 58.33+tol))[0]
lo0 = np.where((lon_all >= 22.79-tol) & (lon_all <= 23.99+tol))[0]

def pool_for(li, lo):
    out = []
    for Y in range(1992, 2003):
        b = date(Y, 6, 1)
        for k in range(-5, 6):
            d = b + timedelta(days=k)
            i = int(np.searchsorted(ds.time.values, np.datetime64(f"{d.year:04d}-{d.month:02d}-{d.day:02d}")))
            out.append(float(ds.analysed_sst[i, li, lo].values))
    return np.array(out)

li, lo = int(li0[0]), int(lo0[0])
pool = pool_for(li, lo)
n = int(np.isfinite(pool).sum())
if n == 0:
    for c2 in range(ncells):
        li2, lo2 = int(li0[c2//60]), int(lo0[c2%60])
        i = int(np.searchsorted(ds.time.values, np.datetime64('2000-06-01')))
        if np.isfinite(float(ds.analysed_sst[i, li2, lo2].values)):
            li, lo, pool, n = li2, lo2, pool_for(li2, lo2), None
            pool = pool_for(li2, lo2)
            n = int(np.isfinite(pool).sum())
            break
cidx = (np.where(li0 == li)[0][0]) * len(li0) + int(np.where(lo0 == lo)[0][0])
print("verify cell (li,lo) =", li, lo, " flat idx", cidx)

xs_all = pool[np.isfinite(pool)]
h1 = min(max(n*0.9 + 0.5, 1.0), float(n))
lo_i = int(np.floor(h1)); frac = h1 - lo_i
xs = np.sort(xs_all)
q_manual = xs[-1] if lo_i >= n else xs[lo_i-1] + frac*(xs[lo_i]-xs[lo_i-1])
print("n =", n, " manual hazen =", q_manual, " pipeline thr =", thr[152, cidx],
      " match:", np.isclose(q_manual, thr[152, cidx]))
print("mean manual =", np.nanmean(pool), " pipeline clim =", clim[152, cidx],
      " match:", np.isclose(np.nanmean(pool), clim[152, cidx]))
ds.close()

# ---------- fixed smoothing ----------
off = np.arange(-15, 16)
idxm = (np.arange(366)[:,None] + off[None,:]) % 366
thr_s = thr[idxm].mean(axis=1)
clim_s = clim[idxm].mean(axis=1)
print("shapes:", thr_s.shape, clim_s.shape)
expect = np.concatenate([thr[351:366], thr[0:15]]).mean()
print("wrap check day1:", thr_s[0,cidx], expect, np.isclose(thr_s[0,cidx], expect))
expect2 = thr[84:115].mean()
print("mid check day100:", thr_s[99,cidx], expect2, np.isclose(thr_s[99,cidx], expect2))

# ---------- sea cells ----------
sea = np.isfinite(tgt).all(axis=0)
print("sea cells:", sea.sum(), "of", ncells)

# ---------- hot days ----------
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
doy_t = np.array([cum[int(s[5:7])-1] + int(s[8:10]) for s in tgt_dates])
print("target doys:", doy_t[0], "..", doy_t[-1])
hot = np.zeros(tgt.shape, dtype=bool)
for i in range(tgt.shape[0]):
    hot[i] = tgt[i] >= thr_s[doy_t[i]-1]
hot &= sea[None, :, :]
print("total hot cell-days:", int(hot.sum()))

# ---------- per-cell MHW: runs >=5, merge gaps of 1-2 ----------
nt = tgt.shape[0]
mem = np.zeros((nt, ncells), dtype=bool)
for c in range(ncells):
    h = hot[:, c]
    if not h.any():
        continue
    dh = np.diff(np.concatenate(([0], h.view(np.int8), [0])))
    starts = np.where(dh == 1)[0]
    ends   = np.where(dh == -1)[0]
    keep = ends - starts >= 5
    if not keep.any():
        continue
    starts = starts[keep]; ends = ends[keep]
    ms = [starts[0]]; me = [ends[0]]
    for s, e in zip(starts[1:], ends[1:]):
        if s - me[-1] in (1, 2):
            me[-1] = e
        else:
            ms.append(s); me.append(e)
    for s, e in zip(ms, me):
        mem[s:e, c] = True
print("mask cell-days in MHW:", int(mem.sum()))

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
np.savez_compressed('/work/mhw.npz', mem=mem, active=active, sea=sea,
                    tgt_dates=tgt_dates, thr_s=thr_s, clim_s=clim_s)
print("saved mhw.npz")
'''
open('/work/pipeline2.py','w').write(script)
import runpy
runpy.run_path('/work/pipeline2.py', run_name='__main__')
