import numpy as np
import pickle
import time as _time
import calendar
from datetime import date

with open('/work/data.pkl','rb') as f:
    D = pickle.load(f)
V_win = D['V_win']; V_tgt = D['V_tgt']
tw = D['time_win'].astype('datetime64[D]')
tt = D['time_tgt'].astype('datetime64[D]')

LEAP = 2000
md2doy = {}
for m in range(1,13):
    for dd in range(1, calendar.monthrange(LEAP, m)[1]+1):
        md2doy[(m,dd)] = (date(LEAP,m,dd) - date(LEAP,1,1)).days + 1
def doys_of(t64):
    obj = t64.astype(object)
    return np.array([md2doy[(int(o.month), int(o.day))] for o in obj], dtype=int)

doy_win = doys_of(tw)
doy_tgt = doys_of(tt)
assert list(doy_win[:5]) == [362,363,364,365,366]
assert list(doy_win[5:10]) == [1,2,3,4,5]
assert list(doy_win[-5:]) == [1,2,3,4,5]
print("win doys first/last:", doy_win[0], doy_win[-1], "| tgt doys first/last:", doy_tgt[0], doy_tgt[-1])

P = np.zeros(len(doy_win), dtype=int)
P[5:4023] = doy_win[5:4023]
assert int((P>0).sum()) == 4018

V2 = V_win.reshape(4028, 3600)
sea2 = np.all(np.isfinite(V_tgt), axis=0).reshape(3600)
Vsea = V2[:, sea2]
fin_counts = np.isfinite(V2).sum(axis=0)
print("sea cells:", sea2.sum(), "| cells with any NaN in window:", (fin_counts < 4028).sum(), "min fin count:", fin_counts.min())

t0=_time.time()
thr = np.full(367, np.nan)
clim = np.full(367, np.nan)
for d in range(1, 367):
    if d == 60:
        continue
    js = np.where(P == d)[0]
    assert js.size == 11, (d, js.size)
    idx = np.concatenate([np.arange(j-5, j+6) for j in js])
    assert len(idx) == 121
    pool = Vsea[:, idx]
    thr[d] = np.nanquantile(pool, 0.90, method='hazen', axis=1)
    clim[d] = np.nanmean(pool, axis=1)
print("thresholds computed in %.1fs; NaN thr cells: %d, NaN clim cells: %d" %
      (_time.time()-t0, np.isnan(thr[1:]).sum(axis=1).sum(), np.isnan(clim[1:]).sum(axis=1).sum()))
print("thr doy182 mean/median: %.3f %.3f | clim doy182 mean: %.3f" % (thr[182].mean(), np.median(thr[182]), clim[182].mean()))

with open('/work/thr.pkl','wb') as f:
    pickle.dump({'thr': thr, 'clim': clim, 'sea2': sea2, 'doy_tgt': doy_tgt,
                 'time_win': D['time_win'], 'time_tgt': D['time_tgt'],
                 'lat': D['lat'], 'lon': D['lon'], 'V_tgt': V_tgt}, f)
print("saved")
