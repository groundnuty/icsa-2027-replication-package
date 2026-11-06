import datetime as dt
def doy_cal(d):
    k = (d.month - 1) * 31 + (4*(d.month-1) - 1)//7 - ((d.month - 1) * 5 + 3)//16 + d.day
    assert 1 <= k <= 366, (d, k)
    # sanity vs datetime.toordinal fixups
    return k
# verify against manual mapping
import calendar
md2doy = {}
day = 0
for y in [2004]:
    for m in range(1, 13):
        for dd in range(1, calendar.monthrange(y, m)[1] + 1):
            day += 1
            md2doy[(m, dd)] = day
ok = True
for m in range(1, 13):
    for dd in range(1, 32):
        try:
            d = dt.date(2004, m, dd)
        except ValueError:
            continue
        if doy_cal(d) != md2doy[(m, dd)]:
            print('MISMATCH', d, doy_cal(d), md2doy[(m, dd)])
            ok = False
print('doy formula ok:', ok)
# Feb 28/29 and Mar 1
for s in ['2004-02-28','2004-02-29','2004-03-01','2003-02-28','2003-03-01','1992-12-31']:
    y, m, dd = map(int, s.split('-'))
    print(s, doy_cal(dt.date(y, m, dd)))
