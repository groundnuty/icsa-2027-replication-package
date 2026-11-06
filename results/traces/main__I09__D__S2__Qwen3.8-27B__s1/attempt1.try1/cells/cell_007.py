import numpy as np
import pandas as pd
print("numpy:", np.__version__, "pandas:", pd.__version__)

# hazen check: pool n=121 values 0..120, p=0.9 -> h=(n+1)*p = 109.8 (1-indexed)
a = np.arange(121, dtype=float)
q = np.quantile(a, 0.9, method='hazen')
print("hazen quantile of 0..120:", q, "(expect 108.8)")
qn = np.nanquantile(np.c_[a, np.array([np.nan]*121)], 0.9, axis=0, method='hazen')
print("nanquantile ignoring NaN col:", qn[:5])

# DOY mapping test
def doy_of(dates):
    t = pd.to_datetime(dates)
    m = t.month.to_numpy(); d = t.day.to_numpy()
    ref = pd.to_datetime(dict(year=2020, month=m, day=d)) - pd.Timestamp('2020-01-01')
    return ref.days + 1

tests = pd.to_datetime(['1992-01-01','2001-02-28','2000-02-29','2001-03-01','1993-12-31','2022-06-01','2022-08-31','1992-02-28','2020-02-29'])
print("DOYs:", doy_of(tests))
print("expect: [1, 59, 60, 61, 366, 153, 244, 59, 60]")
