script = '''
import numpy as np
z = np.load('/work/interim.npz', allow_pickle=True)
thr = z['thr']; clim = z['clim']
tgt = z['tgt']
tgt_dates = np.asarray(z['tgt_dates'], dtype=str)
ncells = 3600
cidx = 22

# ---------- smoothing (fixed) ----------
off = np.arange(-15, 16)
idxm = (np.arange(366)[:,None] + off[None,:]) % 366
thr_s = thr[idxm].mean(axis=1)   # (366, 3600)
clim_s = clim[idxm].mean(axis=1)
print("shapes:", thr_s.shape, clim_s.shape)
expect = np.concatenate([thr[351:366, cidx], thr[0:15, cidx]]).mean()
print("wrap check day1 cell", cidx, ":", thr_s[0,cidx], expect, np.isclose(thr_s[0,cidx], expect))
expect2 = thr[84:115, cidx].mean()
print("mid check day100 cell", cidx, ":", thr_s[99,cidx], expect2, np.isclose(thr_s[99,cidx], expect2))
# also verify day 366 window: 352..366,1..14  (d=366: d-15=351(1-based)-> idx 350 .. d+15=381 mod 366 = 15)
expect3 = thr[(np.arange(366)-15+366)%366][244-1-15 if False else 365-15:366, cidx].mean() if False else None
# day 366 (idx 365): window idx (365-15..365) + (0..14)
expect3 = np.concatenate([thr[350:366, cidx], thr[0:15, cidx]]).mean()
print("day366 check:", thr_s[365,cidx], expect3, np.isclose(thr_s[365,cidx], expect3))

# ---------- sea cells ----------
sea = np.isfinite(tgt).all(axis=0)
print("sea cells:", sea.sum(), "of", ncells)

# ---------- hot days ----------
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
doy_t = np.array([cum[int(s[5:7])-1] + int(s[8:10]) for s in tgt_dates])
print("target doys:", doy_t[0], "..", doy_t[-1])
hot = np.zeros(tgt.shape, dtype=bool)
for i in range(tgt.shape[0]):
    hot[i] = tgt[i] >= thr_s[doy_t[i]-1].reshape(60, 60)
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
open('/work/pipeline3.py','w').write(script)
import runpy
runpy.run_path('/work/pipeline3.py', run_name='__main__')
