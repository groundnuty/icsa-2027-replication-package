import numpy as np, os
B = np.load('work/B.npy'); T = np.load('work/T.npy')
bdays = np.load('work/bdays.npy'); tdays = np.load('work/tdays.npy')
import datetime as dt
bdates = [dt.date(1970,1,1)+dt.timedelta(days=int(k)) for k in bdays]
tdates = [dt.date(1970,1,1)+dt.timedelta(days=int(k)) for k in tdays]
print("cache OK | B:", B.shape, B.dtype, "| T:", T.shape, "| bdates:", bdates[0], bdates[-1], "| tdates:", tdates[0], tdates[-1])
print("B finite frac:", np.isfinite(B).mean(), "| T finite frac:", np.isfinite(T).mean())

def leap(y): return y%4==0 and (y%100!=0 or y%400==0)
def doy_of(d):
    n = (d - dt.date(d.year,1,1)).days + 1
    if d.month >= 3 and not leap(d.year): n += 1
    return n
bdoy = np.array([doy_of(d) for d in bdates], dtype=np.int64)  # (nbase,)
print("baseline doy range:", bdoy.min(), bdoy.max(), "| counts per doy (unique):", np.unique(np.bincount(bdoy, minlength=367))[1:])
# check: no baseline date maps to 60 (1992,1996,2000 are leap: Feb29 -> 60!)
print("n baseline dates mapping to doy 60:", (bdoy==60).sum())
print("those dates:", [bdates[i] for i in np.where(bdoy==60)[0]][:5])
