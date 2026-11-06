
import numpy as np, time
from datetime import date, timedelta

t0 = time.time()
buf = np.concatenate([np.load(f'/work/b{i}.npy') for i in (1,2,3)], axis=0).reshape(-1, 3600)
tgt = np.load('/work/b4.npy').reshape(92, 3600)

def get_dates(d0, d1):
    out, cur = [], d0
    while cur <= d1:
        out.append(cur); cur += timedelta(days=1)
    return out
buf_dates = get_dates(date(1991,12,27), date(2003,1,5))
tgt_dates = get_dates(date(2019,6,1), date(2019,8,31))

sea = np.isfinite(tgt).all(axis=0)
print("sea cells:", int(sea.sum()))
bs = buf[:, sea]  # (4028, 3311)
sea_nan_cells = np.isfinite(bs).all(axis=0)
print("sea cells with any baseline NaN:", int((~sea_nan_cells).sum()))
nan_by_date = (~np.isfinite(bs)).sum(axis=1)
nz = np.where(nan_by_date > 0)[0]
print("baseline days with sea-cell NaNs:", len(nz), "first:", [buf_dates[i].isoformat() for i in nz[:5]], "max per day:", int(nan_by_date.max()))
np.save('/work/sea.npy', sea)
np.save('/work/bs.npy', bs)
np.save('/work/tg.npy', tgt)
print("time %.1f s" % (time.time()-t0))
