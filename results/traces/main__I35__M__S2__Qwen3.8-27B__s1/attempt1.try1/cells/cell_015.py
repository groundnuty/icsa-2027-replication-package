import numpy as np
from datetime import date, timedelta

PREF = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_py(y, m, d):
    return PREF[m-1] + d

X = np.load("/tmp/X.npy")
cand = np.datetime64("1991-12-27") + np.arange(X.shape[0])
cand_py = [date(1991,12,27) + timedelta(days=int(i)) for i in range(X.shape[0])]
b_start, b_end = date(1992,1,1), date(2002,12,31)

M = np.load("/tmp/M.npy")

# brute-force pool dates for a few doy values
def brute_pool(d):
    s = set()
    for t in cand_py:
        if b_start <= t <= b_end and doy_py(t.year, t.month, t.day) == d:
            for o in range(-5, 6):
                s.add(t + timedelta(days=o))
    return s

for d in [1, 55, 59, 60, 61, 183, 366]:
    exp = brute_pool(d)
    got = set(cand_py[i] for i in np.where(M[d-1])[0])
    print("doy", d, "size", len(exp), "match:", exp == got)
