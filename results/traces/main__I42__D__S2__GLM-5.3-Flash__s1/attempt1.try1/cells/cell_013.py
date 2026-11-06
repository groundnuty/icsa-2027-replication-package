import numpy as np, pandas as pd

z = np.load('/work/clim_thr.npz')
thr, clim, sea, tgt_doy = z['thr'], z['clim'], z['sea'], z['tgt_doy']
sst_tgt = np.load('/work/sst_tgt.npy').astype(np.float64)
tgt_dates = pd.read_pickle('/work/tgt_dates.pkl')

# correct smoothing: 366-element array (days 1..366), wrap modulo 366
def smooth31(pre):           # pre: (367,60,60), index 0 unused
    p = pre[1:367]           # (366,60,60): index i -> day i+1
    out = np.zeros_like(p)
    for off in range(-15,16):
        out += np.roll(p, off, axis=0)
    out /= 31.0
    full = np.full_like(pre, np.nan)
    full[1:367] = out
    return full

thr_s, clim_s = smooth31(thr), smooth31(clim)
print("smoothed thr/clim finite on sea cells, all 366 doys:",
      bool(np.isfinite(thr_s[1:][:, sea]).all()), bool(np.isfinite(clim_s[1:][:, sea]).all()))

# check: target doy values unchanged vs previous (buggy) version for doys 16..351
old = np.load('/work/clim_thr.npz')['thr_s']
sel = np.arange(16, 352)
print("thr_s identical to previous version for doys 16..351:",
      bool(np.array_equal(thr_s[sel], old[sel], equal_nan=True)))
print("clim_s identical to previous version for doys 16..351:",
      bool(np.array_equal(clim_s[sel], np.load('/work/clim_thr.npz')['clim_s'][sel], equal_nan=True)))

nd = len(tgt_dates)
thr_days = thr_s[tgt_doy]
hot = (sst_tgt >= thr_days) & sea[None,:,:]
print("hot-day fraction on sea cells:", float(hot[:, sea].mean()))

def find_runs(f, minlen):
    runs=[]; n=len(f); i=0
    while i < n:
        if f[i]:
            j=i
            while j+1<n and f[j+1]: j+=1
            if j-i+1>=minlen: runs.append([i,j])
            i=j+1
        else: i+=1
    return runs

def join_runs(runs, maxgap):
    if not runs: return []
    m=[runs[0][:]]
    for s,e in runs[1:]:
        gap = s-m[-1][1]-1
        if 1 <= gap <= maxgap: m[-1][1]=e
        else: m.append([s,e])
    return m

per_cell = np.zeros((nd,60,60), bool)
n_mhw=0
for ci in range(60):
    for cj in range(60):
        if not sea[ci,cj]: continue
        evs = join_runs(find_runs(hot[:,ci,cj],5), 2)
        n_mhw += len(evs)
        for s,e in evs: per_cell[s:e+1,ci,cj]=True
print("per-cell MHW events total:", n_mhw)

active = per_cell.any(axis=(1,2))
regional = join_runs(find_runs(active,1),0)
print("active days:", int(active.sum()))
print("regional events:", len(regional))
for s,e in regional:
    print("  ", tgt_dates.iloc[s].date(), "->", tgt_dates.iloc[e].date(), f"({e-s+1} days)")
    hot_days = [tgt_dates.iloc[k].date().isoformat() for k in range(s,e+1) if hot[k].any()]
    print("   days with >=1 hot cell:", hot_days)
# which cells are in MHW on active days?
for s,e in regional:
    for k in range(s,e+1):
        cnt = per_cell[k].sum()
        print(f"  {tgt_dates.iloc[k].date()}: cells in MHW = {int(cnt)}")

np.savez('/work/final.npz', thr_s=thr_s, clim_s=clim_s, per_cell=per_cell, hot=hot, sea=sea)
print("saved final.npz")
