import datetime as dt, json, os
# map slot s (1..366) -> list of baseline dates within +-5 cal days of any date whose shifted doy is s
def doy_cal(d):
    CUM = [0,31,59,90,120,151,181,212,243,273,304,334]
    k = CUM[d.month-1] + d.day
    if d.month > 2 and d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0):
        k += 1
    return k
def doy_shift(k):
    if k <= 59: return k + 1
    if k == 60: return 0
    return k
# dates with shifted doy s: for s<=59: non-leap k=s-1; s==60: leap k=60 (Feb29); s>=61: k=s (any year)
slot_dates = {}
for s in range(1, 367):
    if s <= 59:
        ks = [s-1]; leaps = [False]
    elif s == 60:
        ks = [60]; leaps = [True]
    else:
        ks = [s]; leaps = [False, True]
    ds = []
    for k, leap in zip(ks, leaps):
        for y in range(1992, 2003):
            if leap and y % 4 != 0:  # (all 1992-2002 leap candidates: 1992,1996,2000)
                continue
            # find date with cal doy k in year y
            d = dt.date(y,1,1) + dt.timedelta(days=k-1)
            # verify
            if leap:
                assert (d.month, d.day) == (2,29), (y,k,d)
            ds.append(d)
    slot_dates[s] = ds
# windows: union over pool members
pool_window = {}
for s in range(1, 367):
    w = set()
    for d0 in slot_dates[s]:
        for off in range(-5, 6):
            w.add(d0 + dt.timedelta(days=off))
    pool_window[s] = sorted(w)
# report structure
sizes = [len(pool_window[s]) for s in range(1, 367)]
import collections
print('window sizes: min', min(sizes), 'max', max(sizes))
print('size of slot 60 pool window:', len(pool_window[60]))
# check ends
print('slot 2 window:', pool_window[2][0], '->', pool_window[2][-1], len(pool_window[2]))
print('slot 366 window:', pool_window[366][0], '->', pool_window[366][-1], len(pool_window[366]))
# all within [1991-12-27, 2003-01-05]?
allw = set()
for s in range(1, 367): allw.update(pool_window[s])
print('overall range:', min(allw), max(allw), 'total days', len(allw))
# expected: 1991-12-27..2003-01-05 = 365+366+365+365+365+366+365+365+365+365+365+5 = ?
tot = 0
y = 1991
import calendar
for yy in range(1991, 2004):
    if yy == 1991: tot += 5  # Dec 27-31
    elif yy == 2003: tot += 5
    else: tot += 366 if calendar.isleap(yy) else 365
print('expected total distinct days:', tot)
# count how many target dates use which slot: verify slot for 2004-06-01 etc.
def slot_of_date(d):
    k = doy_cal(d)
    s = doy_shift(k)
    return s if s else 60
for test in ['2004-06-01','2004-08-31','2004-02-29','2004-07-15','2004-03-01']:
    y,m,dd = map(int, test.split('-'))
    print(test, '-> slot', slot_of_date(dt.date(y,m,dd)))
