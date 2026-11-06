import numpy as np
import pandas as pd

def doy_of(dates):
    t = pd.to_datetime(dates)
    m = t.month.to_numpy(); d = t.day.to_numpy()
    ref = pd.to_datetime(dict(year=2020, month=m, day=d)) - pd.Timestamp('2020-01-01')
    return ref.dt.days.to_numpy() + 1

tests = pd.to_datetime(['1992-01-01','2001-02-28','2000-02-29','2001-03-01','1993-12-31','2022-06-01','2022-08-31','1992-02-28','2020-02-29'])
print("DOYs:", doy_of(tests))
print("expect: [1 59 60 61 366 153 244 59 60]")
