import numpy as np
from datetime import date, timedelta

b0 = date(1991,12,27)
nb = 4028

# Fixed month/day -> doy mapping (366-day calendar, Feb29=60, Mar1=61, Dec31=366)
CUM = [0,31,59,91,121,152,182,213,243,274,304,335]
def doy_of(d):
    return CUM[d.month-1] + d.day
# checks
for dt, exp in [(date(2000,1,1),1),(date(2000,2,28),59),(date(2000,2,29),60),(date(2000,3,1),61),
                (date(1999,3,1),61),(date(1999,12,31),366),(date(2005,6,1),153),(date(2005,8,31),244),
                (date(1999,2,28),59)]:
    got = doy_of(dt)
    print(dt, got, "OK" if got==exp else "MISMATCH")

def monthday(d):
    if d <= 31: return (1, d)
    if d <= 59: return (2, d-31)
    ref = date(2000,3,1) + timedelta(days=d-61)
    return (ref.month, ref.day)
# roundtrip checks
for dd in [1,31,32,59,61,152,153,244,335,336,366]:
    m,day = monthday(dd)
    print("doy",dd,"->",m,day,"-> doy",doy_of(date(2000,m,day)))
