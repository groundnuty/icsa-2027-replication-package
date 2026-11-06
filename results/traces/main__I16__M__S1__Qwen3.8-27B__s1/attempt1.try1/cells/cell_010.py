import numpy as np, datetime as dt
from datetime import date

Xall = np.load("/tmp/Xall.npy")
NB = 4028
X_b = Xall[:NB]

def doy(d):  # leap-year calendar position
    return date(2000,d.month,d.day).toordinal() - date(2000,1,1).toordinal() + 1

days = [date(1991,12,27)+dt.timedelta(i) for i in range(NB)]
base_start, base_end = date(1992,1,1), date(2002,12,31)

B = np.zeros((366, NB), dtype=bool)
for k in range(-5, 6):
    m = [i for i in range(NB) if base_start <= days[i]+dt.timedelta(k) <= base_end]
    dts = np.array([doy(days[i]+dt.timedelta(k)) for i in m])
    B[dts-1, np.array(m)] = True

rowsums = B.sum(axis=1)
print("rows with 121:", int((rowsums==121).sum()), "| row60 sum:", int(rowsums[59]), "| odd rows:", rowsums[rowsums!=121].tolist()[:10])

idx1 = np.nonzero(B[0])[0]
print("day1 window head:", [str(days[i]) for i in idx1[:8]], "tail:", [str(days[i]) for i in idx1[-6:]])
idx366 = np.nonzero(B[365])[0]
print("day366 window tail:", [str(days[i]) for i in idx366[-6:]])
d59 = [days[i] for i in np.nonzero(B[58])[0]]
print("day59 includes 1992-02-29:", date(1992,2,29) in d59, "| n:", len(d59))
d61 = [days[i] for i in np.nonzero(B[60])[0]]
print("day61 includes 1992-02-29:", date(1992,2,29) in d61, "| n:", len(d61))
np.save("/tmp/B.npy", B)
print("saved B", B.shape)
