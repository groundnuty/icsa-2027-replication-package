import numpy as np, pandas as pd
zb = np.load("work/baseline.npz")
T = pd.DatetimeIndex(zb["time"].astype("datetime64[D]"))

def doy(dts):
    dts = np.asarray(dts, dtype="datetime64[D]")
    yi = pd.DatetimeIndex(dts)
    y, m, d = yi.year.to_numpy(), yi.month.to_numpy(), yi.day.to_numpy()
    jan1 = np.array([np.datetime64(f"{yy}-01-01","D") for yy in y])
    ord_janfeb = (dts - jan1).astype("timedelta64[D]").astype(np.int64) + 1   # valid for m<=2
    # virtual leap-year layout for m>=3: map (m,d) into leap year 2004
    virt = np.array([np.datetime64("2004-01-01","D") + (mm-1)*np.datetime64(0,"D") for mm in m])  # placeholder
    # simpler: build via pandas Timestamp
    virt = np.array([pd.Timestamp(2004, int(mm), int(dd)) for mm, dd in zip(m, d)]).astype("datetime64[D]")
    ord_leap = (virt - np.datetime64("2004-01-01","D")).astype("timedelta64[D]").astype(np.int64) + 1
    return np.where(m <= 2, ord_janfeb, ord_leap)

doyT = doy(T)
for ds_ in ["1991-12-27","1991-12-31","1992-01-01","1992-02-28","1992-02-29","1992-03-01","1993-03-01","2001-02-28","2001-03-01","2001-12-31","2002-12-31","2003-01-05"]:
    print(ds_, "->", int(doyT[T.get_loc(np.datetime64(ds_))]))
base = (T >= np.datetime64("1992-01-01")) & (T <= np.datetime64("2002-12-31"))
from collections import Counter
c = Counter(doyT[base].tolist())
print("baseline days:", int(base.sum()), "| doy60:", c[60], "doy366:", c[366], "doy365:", c[365])
leap_days = [str(T[i].date()) for i in np.where(base & (doyT==60))[0]]
print("doy60 dates in baseline:", leap_days)
np.save("work/doyT.npy", doyT); np.save("work/base_mask.npy", base.astype(bool))
print("saved")
