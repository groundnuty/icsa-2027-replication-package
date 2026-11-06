from datetime import date, timedelta
def daterange(a,b):
    out=[]; d=a
    while d<=b:
        out.append(d); d+=timedelta(days=1)
    return out
bd_ext = daterange(date(1991,12,27), date(2003,1,5))
target_dates = daterange(date(2013,6,1), date(2013,8,31))
print(len(bd_ext), len(target_dates), len(bd_ext)+len(target_dates))
print(bd_ext[0], bd_ext[-1], target_dates[0], target_dates[-1])
cum = [0,31,60,91,121,152,182,213,244,274,305,335]
def key(dt): return cum[dt.month-1] + dt.day
print("key checks:")
for dt,k in [(date(1992,1,1),1),(date(1993,2,28),59),(date(1992,2,29),60),(date(1994,3,1),61),(date(2000,12,31),366),(date(1993,12,31),366)]:
    print(dt, key(dt), "expected", k)
