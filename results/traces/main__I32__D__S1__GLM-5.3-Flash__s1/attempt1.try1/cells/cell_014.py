import numpy as np
from datetime import date, timedelta

CUM366 = [0,31,60,91,121,152,182,213,243,274,305,335]  # cum days before month m in the 366-cal
def doy_of(d):
    return CUM366[d.month-1] + d.day
for dt, exp in [(date(2000,1,1),1),(date(2000,2,28),59),(date(2000,2,29),60),(date(2000,3,1),61),
                (date(1999,3,1),61),(date(1999,12,31),366),(date(2005,6,1),153),(date(2005,8,31),244),
                (date(1999,2,28),59),(date(1992,2,29),60),(date(1993,12,31),366),(date(2002,1,1),1)]:
    got = doy_of(dt)
    print(dt, got, "OK" if got==exp else "MISMATCH")
def monthday(d):
    if d <= 31: return (1, d)
    if d <= 60: return (2, d-31)
    ref = date(2000,3,1) + timedelta(days=d-61)
    return (ref.month, ref.day)
ok = all(doy_of(date(2000,*monthday(dd)))==dd for dd in range(1,367))
print("roundtrip 1..366:", ok)
