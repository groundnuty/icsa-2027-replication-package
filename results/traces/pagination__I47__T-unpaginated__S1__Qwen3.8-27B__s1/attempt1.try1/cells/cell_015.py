
import numpy as np, json, time, warnings
from datetime import date, timedelta

t0 = time.time()
b1 = np.load('/work/b1.npy'); b2 = np.load('/work/b2.npy'); b3 = np.load('/work/b4.npy'.replace('4','3')); b4 = np.load('/work/b4.npy')
print("loaded", b1.shape, b2.shape, b3.shape, b4.shape)

def get_dates(d0, d1):
    out, cur = [], d0
    while cur <= d1:
        out.append(cur); cur += timedelta(days=1)
    return out

buf_dates = get_dates(date(1991,12,27), date(2003,1,5))
buf = np.concatenate([b1, b2, b3], axis=0)
assert len(buf_dates) == len(buf)
tgt_dates = get_dates(date(2019,6,1), date(2019,8,31))
tgt = b4
assert len(tgt_dates) == len(tgt)

# verify stored dates match json
for nm in ['b1','b2','b3','b4']:
    d = json.load(open(f'/work/{nm}_dates.json'))
    print(nm, d[0], d[-1], len(d))

# --- sea cells: finite on every target day ---
fin = np.isfinite(tgt).all(axis=0)  # (60,60)
sea = fin.ravel()
print("sea cells:", int(sea.sum()), "of 3600")

# check: is finite set identical across all days?
allf = np.isfinite(buf)
same = (allf.all(axis=0) == sea).all()
print("baseline finite-everywhere set == sea set:", bool(same),
      "days with any non-sea NaN:", int((~allf[:, sea]).sum()),
      "baseline NaNs in sea cells:", int((~allf[:, sea]).sum()))
# how many sea cells have NaN somewhere in baseline
sea_nan_cells = np.isfinite(buf[:, sea]).all(axis=0)
print("sea cells with any baseline NaN:", int((~sea_nan_cells).sum()))
tgt_nan_cells = np.isfinite(tgt[:, sea]).all(axis=0)
print("sea cells with any target NaN:", int((~tgt_nan_cells).sum()))
np.save('/work/sea.npy', sea)
print("time %.1f s" % (time.time()-t0))
