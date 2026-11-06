
import datetime as dt
bt=pd.DatetimeIndex(base.time.values)
def doy(t):
    t=pd.Timestamp(t)
    # 1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61 (leap-aware mapping by month/day)
    d=t.dayofyear
    leap=t.is_leap_year
    if leap and (t.month>2): d-=1   # leap years: Mar 1 is doy 61
    return d
# doy by month/day mapping: Mar1 in leap=61, nonleap=60 -> non-leap Mar1 must be 61 too
def doy2(t):
    t=pd.Timestamp(t)
    if t.month==2 and t.day==29: return 60
    d=t.dayofyear
    if t.is_leap_year and t.month>2: d-=1
    if (not t.is_leap_year) and t.month>2: d=d+1  # non-leap: Mar1 -> 61
    return d
# Fix: non-leap Mar1 dayofyear=60 -> +1 gives 61; leap Mar1 dayofyear=61 -> -1 gives 60 -> wrong
def doy3(t):
    t=pd.Timestamp(t)
    if t.month==2 and t.day==29: return 60
    d=t.dayofyear
    if t.month>2 and t.is_leap_year: d-=1  # leap: Mar1 has dayofyear 61 -> 60 wrong
    return d
# Simpler: use explicit table of month/day -> doy with 29 Feb=60
cum=[0,31,59,90,120,151,181,212,243,273,304,334]
def doy_md(t):
    t=pd.Timestamp(t)
    if t.month==2 and t.day==29: return 60
    d=cum[t.month-1]+t.day
    if t.month>2: d+=1  # Mar onward: shift by +1 to account for day 60 skip in non-leap sense
    return d
print([ (s,doy_md(s)) for s in ['2011-01-01','2011-02-28','2012-02-29','2011-03-01','2011-12-31','2012-12-31','2013-06-01','2013-08-31']])
