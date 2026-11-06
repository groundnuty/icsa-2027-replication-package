script = '''
import numpy as np
z = np.load('/work/interim.npz', allow_pickle=True)
thr = z['thr']; clim = z['clim']
tgt = z['tgt']
tgt_dates = np.asarray(z['tgt_dates'], dtype=str)
ncells = 3600
cidx = 22

# ---------- smoothing ----------
off = np.arange(-15, 16)
idxm = (np.arange(366)[:,None] + off[None,:]) % 366
thr_s = thr[idxm].mean(axis=1)
clim_s = clim[idxm].mean(axis=1)
# proper per-cell window checks
for d1 in [1, 100, 366, 30, 70]:
    i = d1 - 1
    win = (i - 15 + np.arange(31)) % 366
    expect = thr[win, cidx].mean()
    ok = np.isclose(thr_s[i, cidx], expect)
    print(f"day {d1}: match={ok} (n={len(win)})")
    assert ok

# ---------- sea cells ----------
sea = np.isfinite(tgt).all(axis=0).ravel()   # (3600,)
print("sea cells:", sea.sum(), "of", ncells)

# ---------- hot days ----------
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
doy_t = np.array([cum[int(s[5:7])-1] + int(s[8:10]) for s in tgt_dates])
nt = tgt.shape[0]
hot = np.zeros((nt, 60, 60), dtype=bool)
for i in range(nt):
    hot[i] = tgt[i] >= thr_s[doy_t[i]-1].reshape(60, 60)
hot = hot.reshape(nt, ncells) & sea[None, :]
print("total hot cell-days:", int(hot.sum()))

# ---------- per-cell MHW: runs >=5, merge gaps of 1-2 ----------
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
print("cells with >=1 MHW:", int(mem.any(axis=0).sum()))
lens = []
for c in range(ncells):
    col = mem[:, c]
    if not col.any(): continue
    dh = np.diff(np.concatenate(([0], col.view(np.int8), [0])))
    st = np.where(dh == 1)[0]; en = np.where(dh == -1)[0]
    lens.extend((en - st).tolist())
lens = np.array(lens)
print("per-cell MHW count:", len(lens), "len min/med/max:", lens.min(), np.median(lens), lens.max())

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
print("active days per event:", [int(mem[a:b+1].any(axis=1).sum()) for a,b in [(list(tgt_dates).index(s), list(tgt_dates).index(e)) for s,e in ev]])
np.savez_compressed('/work/mhw.npz', mem=mem, active=active, sea=sea,
                    tgt_dates=tgt_dates, thr_s=thr_s, clim_s=clim_s)
print("saved mhw.npz")
'''
open('/work/pipeline4.py','w').write(script)
import runpy
runpy.run_path('/work/pipeline4.py', run_name='__main__')
