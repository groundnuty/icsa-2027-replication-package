
import numpy as np, json, time
from datetime import date, timedelta

t0 = time.time()
buf = np.concatenate([np.load(f'/work/b{i}.npy') for i in (1,2,3)], axis=0)
tgt = np.load('/work/b4.npy')

def get_dates(d0, d1):
    out, cur = [], d0
    while cur <= d1:
        out.append(cur); cur += timedelta(days=1)
    return out
buf_dates = get_dates(date(1991,12,27), date(2003,1,5))
tgt_dates = get_dates(date(2019,6,1), date(2019,8,31))

fin = np.isfinite(tgt).all(axis=0).ravel()
sea = fin
print("sea cells:", int(sea.sum()))

sea_nan_cells = np.isfinite(buf[:, sea]).all(axis=0)
print("sea cells with any baseline NaN:", int((~sea_nan_cells).sum()))
allf = np.isfinite(buf)
nan_by_date = (~allf[:, sea]).sum(axis=1)
nz = np.where(nan_by_date > 0)[0]
print("baseline days with sea-cell NaNs:", len(nz), "first:", [buf_dates[i].isoformat() for i in nz[:5]], "max per day:", int(nan_by_date.max()))
np.save('/work/sea.npy', sea)
np.save('/work/buf.npy', buf)
print("time %.1f s" % (time.time()-t0))
