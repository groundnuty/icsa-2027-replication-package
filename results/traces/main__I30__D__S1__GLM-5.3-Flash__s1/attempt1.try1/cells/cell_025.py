import numpy as np, datetime as dt

def doy_map(d):
    leap = (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0))
    return d.timetuple().tm_yday if (leap or d.month < 3) else d.timetuple().tm_yday + 1

def ref_dates(D):
    out = []
    for y in range(1992, 2003):
        d = dt.date(y, 1, 1)
        while d.year == y:
            if doy_map(d) == D:
                out.append(d); break
            d += dt.timedelta(days=1)
    return out

# which D gives size != 121/33 in brute (with duplicates)?
for D in range(1, 367):
    if D == 60: continue
    refs = ref_dates(D)
    if len(refs) != 11:
        print('D', D, 'n refs:', len(refs))
    dates = []
    for r in refs:
        for k in range(-5,6):
            d = r + dt.timedelta(days=k)
            if dt.date(1991,12,27) <= d <= dt.date(2003,1,5):
                dates.append(d)
    exp = 33 if D == 366 else 121
    if len(dates) != exp or len(set(dates)) != exp:
        print('D', D, 'brute n (with dup):', len(dates), 'unique:', len(set(dates)), 'expected:', exp)
print('done')
