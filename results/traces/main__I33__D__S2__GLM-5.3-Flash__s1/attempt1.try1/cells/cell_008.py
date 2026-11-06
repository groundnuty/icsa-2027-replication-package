import numpy as np
from datetime import date, timedelta
ext = np.load('/work/ext.npy')  # (4028, 60, 60) float64, dates 1991-12-27 .. 2003-01-05

def doy_of(y,m,d): return (date(2000,m,d) - date(2000,1,1)).days + 1  # leap-anchored 1..366

d0 = date(1992,1,1); d1 = date(2002,12,31)
base_dates = [d0 + timedelta(days=k) for k in range((d1-d0).days + 1)]
e0 = date(1991,12,27)
def eidx(dt): return (dt - e0).days   # index into ext

# pool date indices per doy
pool = {d: [] for d in range(1, 367)}
for b in base_dates:
    bd = doy_of(b.year, b.month, b.day)
    if bd == 60:   # 29 Feb centres get no pool of their own
        continue
    for o in range(-5, 6):
        p = b + timedelta(days=o)
        cd = doy_of(p.year, p.month, p.day)
        if cd != 60:
            pool[cd].append(eidx(p))

sizes = {d: len(v) for d, v in pool.items()}
print('pool sizes: min', min(sizes.values()), 'max', max(sizes.values()))
print('doy 1 size', sizes[1], '(expect 11: 1991-12-27..1992-01-06)')
print('doy 366 size', sizes[366], '(expect 11: 2002-12-26..2003-01-05)')
print('doy 60 size', sizes[60])
print('doy 153 size', sizes[153], '(expect 121)')
# check: 29 Feb dates present in pools of neighbours only
d029 = [eidx(date(y,2,29)) for y in (1992,1996,2000)]
in_60 = any(i in pool[60] for i in d029)
in_59 = all(i in pool[59] for i in d029)
in_61 = all(i in pool[61] for i in d029)
print('29Feb in pool60:', in_60, '| in pool59:', in_59, '| in pool61:', in_61)

clim_raw = np.full((366, 60, 60), np.nan)
thr_raw  = np.full((366, 60, 60), np.nan)
for d in range(1, 367):
    if d == 60: 
        continue
    idx = np.array(pool[d])
    vals = ext[idx]                       # (n, 60, 60)
    with np.errstate(all='ignore'):
        clim_raw[d-1] = np.nanmean(vals, axis=0)
        thr_raw[d-1]  = np.nanpercentile(vals, 90, axis=0, method='hazen')
np.save('/work/clim_raw.npy', clim_raw); np.save('/work/thr_raw.npy', thr_raw)
print('clim NaN cells (land expected 310):', np.isnan(clim_raw[152]).sum())
# sample sea cell [30,30]
print('doy153 clim/thr raw @[30,30]: %.4f %.4f' % (clim_raw[152,30,30], thr_raw[152,30,30]))
print('doy60 raw is NaN (pre-fill):', np.isnan(clim_raw[59]).all(), np.isnan(thr_raw[59]).all())