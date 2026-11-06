import numpy as np, pandas as pd

d = np.load("work/coords.npz"); t_tgt = pd.to_datetime(d['t_tgt'])
lat, lon = d['lat'], d['lon']
c = np.load("work/clim.npz"); thr, sea, tgt = c['thr'], c['sea'], c['tgt']
m = np.load("work/mhw.npz"); mhw, hot, active, doy = m['mhw'], m['hot'], m['active'], m['doy']
nt = len(t_tgt)

# independent re-derivation of active runs
runs = []
i = 0
while i < nt:
    if active[i]:
        j = i
        while j+1 < nt and active[j+1]: j += 1
        runs.append((i,j)); i = j+1
    else: i += 1
print("active idx runs:", runs)
for s,e in runs:
    print("  dates:", str(t_tgt[s].date()), "->", str(t_tgt[e].date()), "len", e-s+1)
print("cnt[30..50]:")
for i in range(30, 51):
    print(f"  idx {i} {str(t_tgt[i].date())} doy {doy[i]} cells_in_mhw {int(mhw[i].sum())} hot {int(hot[i].sum())} active {bool(active[i])}")
