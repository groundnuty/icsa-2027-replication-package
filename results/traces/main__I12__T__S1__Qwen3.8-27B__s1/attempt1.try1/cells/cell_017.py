import numpy as np, datetime as dt
z = np.load('data/climthr.npz')
res = np.load('data/results.npz')
hot, active, mhw = res['hot'], res['active'], res['mhw']
SST_tgt = np.load('data/SST_tgt.npy')
thr_smooth = z['thr_smooth']; tgt_doy = z['tgt_doy']; sea = z['sea']

def daterange(a, b):
    d = a
    while d <= b:
        yield d; d += dt.timedelta(days=1)
tgt_dates = list(daterange(dt.date(2009,6,1), dt.date(2009,8,31)))

hc = hot.sum(axis=(1,2))
print('daily hot cell counts:')
for i in range(92):
    mark = 'A' if active[i] else ' '
    print(f'{tgt_dates[i]} doy={tgt_doy[i]:3d} hot={hc[i]:4d} {mark}')