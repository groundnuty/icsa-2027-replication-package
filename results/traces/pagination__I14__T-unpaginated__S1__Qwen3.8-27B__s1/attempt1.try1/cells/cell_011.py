
import datetime as dt
mleap = [31,29,31,30,31,30,31,31,30,31,30,31]
pref = [0]
for m in mleap: pref.append(pref[-1]+m)
def doy(d):
    return pref[d.month-1] + d.day
for test in [dt.date(2000,1,1), dt.date(2000,2,28), dt.date(2000,2,29), dt.date(2000,3,1), dt.date(2000,12,31), dt.date(1991,12,27), dt.date(2003,1,5)]:
    print(test, doy(test))
