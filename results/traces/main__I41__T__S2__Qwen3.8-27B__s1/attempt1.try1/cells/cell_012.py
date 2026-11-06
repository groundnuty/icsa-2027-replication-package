import numpy as np, pandas as pd, time
t0=time.time()
zb = np.load("work/baseline.npz")
V = zb["sst"]  # (4028, 3600) float64
T = pd.DatetimeIndex(zb["time"].astype("datetime64[D]"))
print("T:", T[0].date(), T[-1].date(), len(T))

def doy(dts):
    """Day of year per task mapping: Jan1=1 ... Feb28=59, Feb29=60, Mar1=61 ... Dec31=366 (leap count)."""
    dts = np.asarray(dts, dtype="datetime64[D]")
    y = pd.DatetimeIndex(dts).year.to_numpy()
    m = pd.DatetimeIndex(dts).month.to_numpy()
    d = pd.DatetimeIndex(dts).day.to_numpy()
    jan1 = np.array([np.datetime64(f"{yy}-01-01","D") for yy in y])
    ord_no_leap = (dts - jan1).astype("timedelta64[D]").astype(int)  # Jan..Feb same as leap
    # for month>=3 use a leap year reference
    leap_ref = np.array([np.datetime64("2004-01-01","D") if mm>=3 else np.datetime64(f"{yy}-01-01","D")
                         for yy,mm in zip(y,m)])
    ord_leap = (dts - leap_ref).astype("timedelta64[D]").astype(int)
    out = np.where(m<=2, ord_no_leap, ord_leap) + 1
    return out

doyT = doy(T)
print("doy of 1992-01-01, 1992-02-28, 1992-02-29, 1992-03-01, 2001-12-31, 1992-12-31, 1991-12-27, 2003-01-05:",
      doyT[[0, 32, 33, 34]] , end=" ")
# find specific dates
for ds_ in ["1992-01-01","1992-02-28","1992-02-29","1992-03-01","2001-12-31","1992-12-31","1991-12-27","2003-01-05","1993-03-01"]:
    i = T.get_loc(np.datetime64(ds_))
    print(ds_, "->", int(doyT[i]), end="  ")
print()
print("unique doys:", np.unique(doyT).min(), np.unique(doyT).max(), len(np.unique(doyT)))

# verify doy counts: baseline 1992..2002
base = (T >= np.datetime64("1992-01-01")) & (T <= np.datetime64("2002-12-31"))
doyB = doyT[base]
from collections import Counter
c = Counter(doyB.tolist())
print("baseline days:", int(base.sum()), "doy60 count:", c.get(60,0), "doy366 count:", c.get(366,0), "doy365 count:", c.get(365,0))
np.save("work/doyT.npy", doyT)
np.save("work/base_mask.npy", base)
print("done", round(time.time()-t0,1),"s")
