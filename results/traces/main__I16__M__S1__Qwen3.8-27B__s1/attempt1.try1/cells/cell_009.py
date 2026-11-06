import numpy as np, datetime as dt
from datetime import date
import pickle

Xall = np.load("/tmp/Xall.npy")
NB, NT, Nc = 4028, 92, 3600
X_b = Xall[:NB]; X_t = Xall[NB:]

def doy(d):
    return date(2000,d.month,d.day).toordinal() - date(2000,1,1).toordinal() + 1

days = [date(1991,12,27)+dt.timedelta(i) for i in range(NB)]
doy_all = np.array([doy(d) for d in days])
base_start = date(1992,1,1); base_end = date(2002,12,31)

B = np.zeros((366, NB), dtype=bool)
for k in range(-5, 6):
    t = np.array([days[i]+dt.timedelta(k) for i in range(NB)])
    m = (t >= base_start) & (t <= base_end)
    B[doy(np.vectorize(lambda x: x)(t[m]) if False else [date.fromordinal(int(x)) for x in t.astype('datetime64[D]')][m] if False else [t[i].item() if hasattr(t[i],'item') else t[i] for i in np.nonzero(m)[0]]), np.nonzero(m)[0]] = True
# that line got ugly; do it cleanly:
B = np.zeros((366, NB), dtype=bool)
for k in range(-5, 6):
    ii = np.arange(NB)
    ts = [days[i]+dt.timedelta(k) for i in ii]
    m = [j for j,tt in enumerate(ts) if base_start <= tt <= base_end]
    if m:
        dts = np.array([doy(ts[j]) for j in m])
        B[dts-1, np.array(m)] = True
rowsums = B.sum(axis=1)
print("rows with 121:", (rowsums==121).sum(), "row60:", rowsums[59], "other nonzero:", set(rowsums[rowsums!=121].tolist()))

# verify day-1 window
idx1 = np.nonzero(B[0])[0]
print("day1 window:", [str(days[i]) for i in idx1[:8]], "...", [str(days[i]) for i in idx1[-6:]])
idx366 = np.nonzero(B[365])[0]
print("day366 window tail:", [str(days[i]) for i in idx366[-6:]])
# verify day 59 includes Feb 29 of leap years
idx59 = np.nonzero(B[58])[0]
d59 = [days[i] for i in idx59]
print("day59 has 1992-02-29:", date(1992,2,29) in d59, "count:", len(d59))
np.save("/tmp/B.npy", B)
print("OK")
