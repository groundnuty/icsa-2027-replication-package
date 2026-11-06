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
P = np.zeros(len(doy_win), dtype=int)
P[5:4023] = doy_win[5:4023]

V2 = V_win.reshape(4028, 3600)
sea2 = np.all(np.isfinite(V_tgt), axis=0).reshape(3600)
Vsea = V2[:, sea2]
K = Vsea.shape[1]
print("sea cells:", K)

t0=_time.time()
thr = np.full((367, K), np.nan)
clim = np.full((367, K), np.nan)
for d in range(1, 367):
    if d == 60:
        continue
    js = np.where(P == d)[0]
    assert js.size == 11, (d, js.size)
    idx = np.concatenate([np.arange(j-5, j+6) for j in js])
    assert len(idx) == 121
    pool = Vsea[idx, :]          # (121, K)
    thr[d] = np.nanquantile(pool, 0.90, method='hazen', axis=0)
    clim[d] = np.nanmean(pool, axis=0)
print("computed in %.1fs; NaN thr cells: %d, NaN clim cells: %d" %
      (_time.time()-t0, int(np.isnan(thr[1:]).sum(axis=1).sum()), int(np.isnan(clim[1:]).sum(axis=1).sum())))
print("thr doy182 mean/median: %.3f %.3f | clim doy182 mean: %.3f" %
      (thr[182].mean(), np.median(thr[182]), clim[182].mean()))

with open('/work/thr.pkl','wb') as f:
    pickle.dump({'thr': thr, 'clim': clim, 'sea2': sea2, 'doy_tgt': doy_tgt,
                 'time_tgt': D['time_tgt'], 'lat': D['lat'], 'lon': D['lon'], 'V_tgt': V_tgt}, f)
print("saved")
