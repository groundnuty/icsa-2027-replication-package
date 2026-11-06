
import datetime as dtm
tim_d = pd.DatetimeIndex(tim)
tgt_mask = (tim_d>=pd.Timestamp('2022-06-01'))&(tim_d<=pd.Timestamp('2022-08-31'))
Tt = A[tgt_mask]; tt_dates = tim_d[tgt_mask]
sea = np.all(np.isfinite(Tt),axis=0)
print("sea cells", sea.sum(), "of", sea.size, "target days", tgt_mask.sum())
# doy mapping
def doy_of(ts):
    # leap-year-based mapping: 1 Jan=1 ... 29 Feb=60 ... 31 Dec=366 ; use 2000 (leap) and map Feb29->60
    d = pd.Timestamp(2000, ts.month, ts.day).dayofyear
    return d
# Note: pd.Timestamp(2000, m, d).dayofyear gives 60 for Feb 29, 61 for Mar 1 -> matches spec
doy_all = np.array([doy_of(x) for x in tim_d])
doy_tgt = doy_all[tgt_mask]
# baseline dates
base_mask = (tim_d>=pd.Timestamp('1992-01-01'))&(tim_d<=pd.Timestamp('2002-12-31'))
bdates = tim_d[base_mask]
print(bdates[0], bdates[-1], base_mask.sum())
# pools: for each date index i in extended range, compute which doy d(!=60) it belongs to
ext_dates = tim_d
# For each baseline date B with doy d != 60, window indices where |D-B|<=5 days
pos = {x:i for i,x in enumerate(tim_d)}
pool_idx = {d: [] for d in range(1,367) if d!=60}
bidx = np.where(base_mask)[0]
for bi in bidx:
    d = doy_all[bi]
    if d==60: continue
    B = tim_d[bi]
    for k in range(-5,6):
        D = B + pd.Timedelta(days=k)
        if D in pos: pool_idx[d].append(pos[D])
print([len(pool_idx[d]) for d in (1,59,61,100,366)])
