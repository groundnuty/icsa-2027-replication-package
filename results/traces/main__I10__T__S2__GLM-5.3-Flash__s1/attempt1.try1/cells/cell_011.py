import numpy as np, pandas as pd

d = np.load("work/coords.npz"); t_tgt = pd.to_datetime(d['t_tgt'])
c = np.load("work/clim.npz")
thr, clm, sea, tgt = c['thr'], c['clm'], c['sea'], c['tgt']
nt = tgt.shape[0]

# explicit month/day -> leap-aligned doy (Feb29=60, Mar1=61, Dec31=366)
CUM = np.array([0,31,59,90,120,151,181,212,243,273,304,334])  # cumulative days before month (leap-style)
months = np.array([ts.month for ts in t_tgt])
days   = np.array([ts.day   for ts in t_tgt])
doy = CUM[months-1] + days
print("doy check:", doy.min(), doy.max(), "n unique:", len(np.unique(doy)))
print("2005-06-01 doy:", doy[0], " 2005-08-31 doy:", doy[-1])

thr_t = thr[:, :, doy-1].transpose(2,0,1)
hot = (tgt >= thr_t) & sea[None,:,:]
hotf = hot.reshape(nt, -1)
mhwf = np.zeros_like(hotf, dtype=bool)
for j in range(hotf.shape[1]):
    col = hotf[:, j]
    if not col.any():
        continue
    starts = list(np.where((~col[:-1]) & col[1:])[0] + 1)
    if col[0]: starts = [0] + starts
    ends = list(np.where(col[:-1] & (~col[1:]))[0])
    if col[-1]: ends = ends + [nt-1]
    assert len(starts) == len(ends)
    hot_runs = [[s, e] for s, e in zip(starts, ends) if e - s + 1 >= 5]
    merged = []
    for r in hot_runs:
        if merged and (r[0] - merged[-1][1] - 1) in (1, 2):
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    for s, e in merged:
        mhwf[s:e+1, j] = True

mhw = mhwf.reshape(nt, 60, 60)
active = mhw.any(axis=(1,2))
print("hot cell-days:", int(hot.sum()), "; mhw cell-days:", int(mhw.sum()))
ev = []
i = 0
while i < nt:
    if active[i]:
        j = i
        while j + 1 < nt and active[j+1]:
            j += 1
        ev.append((i, j)); i = j + 1
    else:
        i += 1
print("active days:", int(active.sum()), "of", nt)
for s, e in ev:
    print("event:", str(t_tgt[s].date()), "to", str(t_tgt[e].date()), f"({e-s+1} days)")
np.savez_compressed("work/mhw.npz", mhw=mhw, hot=hot, active=active)
