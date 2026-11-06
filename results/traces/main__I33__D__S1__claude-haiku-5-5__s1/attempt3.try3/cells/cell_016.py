import datetime
def doy(d):
    leap = (d.year%4==0 and (d.year%100!=0 or d.year%400==0))
    if d.month==2 and d.day==29: return 60
    dd=(d-datetime.date(d.year,1,1)).days+1
    if not leap and dd>=60: dd+=1
    return dd
for d in [datetime.date(1992,2,28),datetime.date(1992,3,1),datetime.date(1992,12,31),datetime.date(1993,12,31),datetime.date(1993,3,1)]:
    print(d, doy(d))