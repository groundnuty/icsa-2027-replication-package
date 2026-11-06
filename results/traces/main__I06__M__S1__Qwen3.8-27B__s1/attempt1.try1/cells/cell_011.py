import numpy as np, datetime as dt
# 1) hazen check on controlled data
x = np.arange(1, 122, dtype=float)
print("numpy hazen 0.9:", np.quantile(x, 0.9, method="hazen"))   # expect 109.85
print("numpy linear 0.9:", np.quantile(x, 0.9, method="linear")) # expect 109.1
# 2) Feb 29 in W_61?
BASE_START = dt.date(1991,12,27)
o = dt.date(1992,3,1).toordinal() - BASE_START.toordinal()
win = np.arange(o-5, o+6)
print("window doy61 1992:", [ (BASE_START+dt.timedelta(days=int(i))).isoformat() for i in win ])
print("1992-02-29 ordinal in window:", (dt.date(1992,2,29).toordinal()-BASE_START.toordinal()) in set(win.tolist()))
