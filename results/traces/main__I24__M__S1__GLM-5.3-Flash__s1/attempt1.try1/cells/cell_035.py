import numpy as np, datetime as dt
thr=np.load('/tmp/thr.npy').reshape(366,60,60)
A=np.load('/tmp/A_all.npy'); ords=np.load('/tmp/dates_ord.npy')
def doy_map(d):
    y=d.timetuple().tm_yday
    leap = d.year%4==0 and (d.year%100!=0 or d.year%400==0)
    return y if leap else (y+1 if y>=60 else y)
doy=np.array([doy_map(dt.date.fromordinal(int(o))) for o in ords])
ti=4540; tj=4631
hot = A[ti:tj+1] >= thr[doy[ti:tj+1]]
# target window boundaries
print('hot on first day (2004-06-01):',int(hot[0].sum()),' last day (2004-08-31):',int(hot[-1].sum()))
print('mhw on first day:',int(np.load("/tmp/inmhw.npy")[0].sum()),' last day:',int(np.load("/tmp/inmhw.npy")[-1].sum()))
# active day diagnostics
inmhw=np.load('/tmp/inmhw.npy')
active=inmhw.any(axis=(1,2))
for k in range(92):
    if active[k]: print(dates[ti+k], 'cells in mhw:',int(inmhw[k].sum()))
# region-level: how many cells ever in mhw
print('cells ever in mhw:',int(inmhw.any(axis=0).sum()),'of 3304 sea cells')
