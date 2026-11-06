import numpy as np, datetime as dt

def dayofyear(d: dt.date) -> int:
    # leap-year-style cumulative mapping: Jan1=1, Feb28=59, Feb29=60, Mar1=61, ..., Dec31=366
    cum = [31,29,31,30,31,30,31,31,30,31,30,31]
    return sum(cum[:d.month-1]) + d.day

for d, exp in [(dt.date(1992,1,1),1),(dt.date(1992,2,28),59),(dt.date(1992,2,29),60),(dt.date(1992,3,1),61),
               (dt.date(2001,12,31),365),(dt.date(2002,12,31),366),(dt.date(1993,3,1),61),(dt.date(1993,2,28),59)]:
    got = dayofyear(d)
    print(d, got, "exp", exp); assert got == exp
print("doy mapping OK")
