from datetime import date, timedelta
CUM366 = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy_of(d): return CUM366[d.month-1] + d.day
for y in (1992, 1999, 2000, 2003, 2005):
    d = date(y,1,1); all_ok = True
    while d.year == y:
        shift = 0 if (y%4==0 or d.month<=2) else 1
        if doy_of(d) != d.timetuple().tm_yday + shift:
            all_ok=False; print("mismatch", d, doy_of(d), d.timetuple().tm_yday); break
        d += timedelta(days=1)
    print(y, "calendar cross-check:", all_ok)
