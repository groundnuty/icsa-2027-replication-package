import numpy as np, datetime as dt, json
print(np.__version__)
# quick check hazen support
a=np.arange(10.0)
print(np.percentile(a,90,method='hazen'))
print(np.quantile(a,0.9,method='hazen'))

A=np.load('/tmp/A_all.npy')
ords=np.load('/tmp/dates_ord.npy')
d0ord=ords[0]
# target slice
t_start=dt.date(2004,6,1).toordinal(); t_end=dt.date(2004,8,31).toordinal()
ti=np.searchsorted(ords,t_start); tj=np.searchsorted(ords,t_end)
assert ords[ti]==t_start and ords[tj]==t_end and tj-ti+1==92
print('target idx',ti,tj)

def doy_map(d):
    dy=d.timetuple().tm_yday
    leap = d.year%4==0 and (d.year%100!=0 or d.year%400==0)
    if leap: return dy
    return dy+1 if dy>=60 else dy
# sanity
for s in ['1993-02-28','1993-03-01','1992-02-28','1992-02-29','1992-03-01','1993-12-31','1992-12-31','1996-12-31']:
    dd=dt.date.fromisoformat(s); print(s, doy_map(dd))
