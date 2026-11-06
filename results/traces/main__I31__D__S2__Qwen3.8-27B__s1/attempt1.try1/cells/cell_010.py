import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
import warnings
warnings.filterwarnings("ignore")

D = np.load('/work/region_data.npz')
base = D['base']; tgt = D['tgt']
t_base = D['t_base']; t_tgt = D['t_tgt']

cum = np.concatenate([[0], np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])])
def doy_of(strs):
    m = np.array([int(s[5:7]) for s in strs]); d = np.array([int(s[8:10]) for s in strs])
    return cum[m-1] + d
doyb = doy_of(t_base); doyt = doy_of(t_tgt)
in_base = (t_base >= "1992-01-01") & (t_base <= "2002-12-31")

thr = np.full((366, 3600), np.nan); clim = np.full((366, 3600), np.nan)
for dd in range(1, 367):
    if dd == 60:
        continue
    idx = np.where((doyb == dd) & in_base)[0]
    pool = np.concatenate([base[i-5:i+6] for i in idx]).reshape(121, 3600)
    thr[dd-1] = np.nanquantile(pool, 0.90, axis=0, method='hazen')
    clim[dd-1] = np.nanmean(pool, axis=0)
thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0

def smooth366(a):
    pad = np.concatenate([a[-15:], a, a[:15]])
    return sliding_window_view(pad, 31, axis=0).mean(axis=-1)
thr_s = smooth366(thr); clim_s = smooth366(clim)

sea = np.isfinite(tgt).all(axis=0).ravel()   # (3600,)
ns = int(sea.sum())
print("sea cells:", ns, "of 3600")
print("non-finite thr_s (sea x days):", int((~np.isfinite(thr_s[:, sea])).sum()),
      "| clim_s:", int((~np.isfinite(clim_s[:, sea])).sum()),
      "| raw thr:", int((~np.isfinite(thr[:, sea])).sum()))

# ---- per-cell MHW over target period ----
T = tgt[:, sea]                      # (92, ns) float64
tht = thr_s[doyt-1][:, sea]          # (92, ns)
hot = T >= tht                       # (92, ns)
print("hot fraction (Jun-Aug):", float(hot.mean()))

mhw = np.zeros((92, ns), bool)
n_cells_with_mhw = 0
for c in range(ns):
    x = hot[:, c].astype(np.int8)
    p = np.concatenate([[0], x, [0]])
    diff = np.diff(p)
    starts = np.where(diff == 1)[0]
    ends   = np.where(diff == -1)[0]   # exclusive
    ev = [[s, e] for s, e in zip(starts, ends) if (e - s) >= 5]
    if not ev:
        continue
    merged = [ev[0]]
    for s, e in ev[1:]:
        if s - merged[-1][1] <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    for s, e in merged:
        mhw[s:e, c] = True
    n_cells_with_mhw += 1
print("cells with >=1 per-cell MHW:", n_cells_with_mhw)

active = mhw.any(axis=1)
# regional events: maximal runs of active days
p = np.concatenate([[0], active.astype(np.int8), [0]])
diff = np.diff(p)
st = t_tgt[np.where(diff == 1)[0]]
en = t_tgt[np.where(diff == -1)[0] - 1]
events = [(str(a), str(b)) for a, b in zip(st, en)]
print("regional events:")
for e in events:
    print("  ", e)
print("total active days:", int(active.sum()))

np.savez_compressed('/work/final_state.npz',
    mhw=mhw, sea=sea, doyt=doyt, t_tgt=t_tgt, lat=D['lat'], lon=D['lon'],
    events_onset=np.array([e[0] for e in events]), events_end=np.array([e[1] for e in events]))
print("saved final state")
