import numpy as np, pandas as pd

d = np.load("work/coords.npz"); t_tgt = pd.to_datetime(d['t_tgt'])
c = np.load("work/clim.npz")
thr, clm, sea, tgt = c['thr'], c['clm'], c['sea'], c['tgt']
nt = tgt.shape[0]

CUM_LEAP = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
doy = CUM_LEAP[np.array([ts.month for ts in t_tgt])-1] + np.array([ts.day for ts in t_tgt])
print("target doys:", doy[0], "..", doy[-1], "(n unique:", len(np.unique(doy)), ")")

thr_t = thr[:, :, doy-1].transpose(2,0,1)
clm_t = clm[:, :, doy-1].transpose(2,0,1)
hot = (tgt >= thr_t) & sea[None,:,:]
print("SST>=climatology fraction at sea cells (context):", float(((tgt >= clm_t) & sea[None,:,:]).sum() / sea.sum() / nt))

hotf = hot.reshape(nt, -1)
mhwf = np.zeros_like(hotf, dtype=bool)
for j in range(hotf.shape[1]):
    col = hotf[:, j]
    if not col.any(): continue
    starts = list(np.where((~col[:-1]) & col[1:])[0] + 1)
    if col[0]: starts = [0] + starts
    ends = list(np.where(col[:-1] & (~col[1:]))[0])
    if col[-1]: ends = ends + [nt-1]
    hot_runs = [[s,e] for s,e in zip(starts,ends) if e-s+1 >= 5]
    merged = []
    for r in hot_runs:
        if merged and (r[0] - merged[-1][1] - 1) in (1,2):
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    for s,e in merged:
        mhwf[s:e+1, j] = True

mhw = mhwf.reshape(nt,60,60)
active = mhw.any(axis=(1,2))
print("hot cell-days:", int(hot.sum()), "; mhw cell-days:", int(mhw.sum()), "; active days:", int(active.sum()), "/", nt)
ev = []
i = 0
while i < nt:
    if active[i]:
        j = i
        while j+1 < nt and active[j+1]: j += 1
        ev.append((i,j)); i = j+1
    else:
        i += 1
print("regional events:", len(ev))
for s,e in ev:
    print("event:", str(t_tgt[s].date()), "to", str(t_tgt[e].date()), f"({e-s+1} days)")
np.savez_compressed("work/mhw.npz", mhw=mhw, hot=hot, active=active, doy=doy)

# per-day active-cell counts for context
print("active cells per active day:", [int(mhw[s:e+1].any(axis=(1,2)).sum()) for s,e in ev])
cnt = mhw.sum(axis=(1,2))
print("cells-in-mhw per day:", cnt.astype(int))
