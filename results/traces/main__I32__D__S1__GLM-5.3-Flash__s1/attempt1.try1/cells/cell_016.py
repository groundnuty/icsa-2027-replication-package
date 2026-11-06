from datetime import date, timedelta
CUM366 = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy_of(d): return CUM366[d.month-1] + d.day
def monthday(d):
    if d <= 31: return (1, d)
    if d <= 60: return (2, d-31)
    ref = date(2000,3,1) + timedelta(days=d-61)
    return (ref.month, ref.day)
ok = all(doy_of(date(2000,*monthday(dd)))==dd for dd in range(1,367))
print("roundtrip 1..366:", ok)
# also cross-check against real calendar doy for leap year 2000 and non-leap 1999
for y in (2000, 1999, 2005):
    d = date(y,1,1); all_ok = True
    while d.year == y:
        if doy_of(d) != d.timetuple().tm_yday + (0 if y%4==0 else 1):
            all_ok=False; print("mismatch", d, doy_of(d), d.timetuple().tm_yday); break
        d += timedelta(days=1)
    print(y, "calendar cross-check:", all_ok)
