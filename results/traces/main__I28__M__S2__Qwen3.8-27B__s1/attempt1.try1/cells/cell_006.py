import numpy as np
import pickle
from datetime import date, timedelta

CUM = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy_spec(m, d):
    return CUM[m-1] + d

pool_start = date(1991,12,27)
N = 4028

M = np.zeros((366, N), dtype=bool)   # row r corresponds to day-of-year r+1
for y in range(1992, 2003):
    leap = (y%4==0 and (y%100!=0 or y%400==0))
    for d in range(1, 367):
        if d == 60:
            continue
        pos = d - 1 if (d > 60 and not leap) else d
        b = date(y,1,1) + timedelta(days=pos-1)
        idx = (b - pool_start).days
        lo = max(0, idx-5); hi = min(N, idx+6)
        M[d-1, lo:hi] = True

print("M[1] count:", M[0].sum(), "(expect 121)")
print("M[59] count:", M[58].sum(), "(expect 121)")
print("M[61] count:", M[60].sum(), "(expect 121)")
assert not M[59].any(), "day 60 must have no pool"
idx_19920229 = (date(1992,2,29)-pool_start).days
print("Feb29 1992 in pools d=59,61:", M[58, idx_19920229], M[60, idx_19920229], "| d=58:", M[57, idx_19920229], "| d=65:", M[64, idx_19920229], "| d=54:", M[53, idx_19920229], "| d=66:", M[65, idx_19920229])
print("M[153] count:", M[152].sum(), "(expect 121)")
print("first/last window for d=1: start idx", M[0].argmax()-0, "-> check idx0 is set:", M[0,0], " end:", N-1-M[0][::-1].argmax())
# d=366 (Dec 31): last window ends 2003-01-05 -> idx 4027
print("M[366] last idx:", N-1-M[365][::-1].argmax(), "(expect 4027)")
np.save("/tmp/M.npy", M)
print("saved M")
