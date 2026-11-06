from datetime import date, timedelta
CUM366 = [0,31,60,91,121,152,182,213,243,274,305,335]
def doy_of(d): return CUM366[d.month-1] + d.day
def monthday(d):
    if d <= 31: return (1, d)
    if d <= 60: return (2, d-31)
    ref = date(2000,3,1) + timedelta(days=d-61)
    return (ref.month, ref.day)
bad = [dd for dd in range(1,367) if doy_of(date(2000,*monthday(dd)))!=dd]
print(bad[:20], len(bad))
for dd in bad[:5]:
    m,day = monthday(dd)
    print(dd, "->", date(2000,m,day), "doy_of:", doy_of(date(2000,m,day)))
