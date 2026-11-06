import datetime as dt, calendar
CUM = [0,31,59,90,120,151,181,212,243,273,304,334]  # days before month, non-leap
def doy_cal(d):
    k = CUM[d.month-1] + d.day
    if d.month > 2 and d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0):
        k += 1
    return k
# verify against full manual mapping for leap and non-leap years
for y in [1992, 1993, 1996, 2000, 2001, 2004]:
    day = 0
    ok = True
    for m in range(1, 13):
        for dd in range(1, calendar.monthrange(y, m)[1] + 1):
            day += 1
            if doy_cal(dt.date(y, m, dd)) != day:
                print('MISMATCH', y, m, dd)
                ok = False
    print(y, 'ok', ok, 'last doy', day, doy_cal(dt.date(y,12,31)))
