import numpy as np
from datetime import date, timedelta
z = np.load("/tmp/sst_data.npz")
B, T = z["B"], z["T"]
btimes = z["btimes"]
def to_date(ts):
    s = str(ts); return date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
base_dates = [to_date(t) for t in btimes]
def doy(d): return (d - date(d.year,1,1)).days + 1
N = B.shape[0]
loaded_idx = {d: i for i, d in enumerate(base_dates)}
M = np.zeros((N, 366), dtype=bool)
for d in base_dates:
    if date(1992,1,1) <= d <= date(2002,12,31):
        d0 = doy(d) - 1
        for k in range(-5, 6):
            M[loaded_idx[d + timedelta(days=k)], d0] = True
counts = M.sum(axis=0)
bad = [d0 for d0 in range(366) if d0 != 59 and counts[d0] != 121]
print("bad cols:", bad, "counts for them:", [counts[d0] for d0 in bad])
print("col 59:", counts[59])
