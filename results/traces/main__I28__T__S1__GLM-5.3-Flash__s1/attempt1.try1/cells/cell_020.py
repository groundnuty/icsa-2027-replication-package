from datetime import date, timedelta
def daterange(a,b):
    out=[]; d=a
    while d<=b:
        out.append(d); d+=timedelta(days=1)
    return out
bd_ext = daterange(date(1991,12,27), date(2003,1,5))
target_dates = daterange(date(2013,6,1), date(2013,8,31))
dates = bd_ext + target_dates
print(len(dates)==4120, dates[0]==date(1991,12,27))
print("dates[4027]:", dates[4027], "== 2002-12-31?", dates[4027]==date(2002,12,31))
print("dates[4028]:", dates[4028], "== 2003-01-01?", dates[4028]==date(2003,1,1))
print("dates[4119]:", dates[4119], "== 2013-08-31?", dates[4119]==date(2013,8,31))
