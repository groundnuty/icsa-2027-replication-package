script = r'''
import numpy as np, datetime as dt
def isleap(y): return y%4==0 and (y%100!=0 or y%400==0)
def doy(d):
    o = (d - dt.date(d.year,1,1)).days + 1
    if not isleap(d.year) and (d.month,d.day) >= (3,1):
        o += 1
    return o
tests = {
 dt.date(1993,1,1):1, dt.date(1993,2,28):59, dt.date(1993,3,1):61, dt.date(1993,12,31):366,
 dt.date(1992,2,29):60, dt.date(1992,3,1):61, dt.date(1992,12,31):366,
 dt.date(2000,2,29):60, dt.date(1996,3,1):61, dt.date(1997,3,1):61,
 dt.date(1993,1,6):6, dt.date(1991,12,31):366, dt.date(1991,12,27):362,
 dt.date(2008,6,1):153, dt.date(2008,8,31):244, dt.date(2008,2,29):60,
}
for d,v in tests.items():
    assert doy(d)==v, (d, doy(d), v)
print('doy mapping OK')
d = dt.date(1982,1,1); bad=0; n60=0
while d <= dt.date(2023,12,31):
    o = doy(d)
    if not (1<=o<=366): bad+=1
    if o==60 and (d.month,d.day)!=(2,29): bad+=1
    if o==60: n60+=1
    d += dt.timedelta(days=1)
print('bad mappings:', bad, 'dates mapping to 60:', n60)
'''
open('/work/doytest.py','w').write(script)
import subprocess
r=subprocess.run(['python','/work/doytest.py'],capture_output=True,text=True)
print(r.stdout); print(r.stderr[-1500:])
