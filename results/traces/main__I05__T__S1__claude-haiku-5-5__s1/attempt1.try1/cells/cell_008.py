import numpy as np, pandas as pd, pickle, os, json
os.makedirs('output',exist_ok=True)
pickle.dump(res, open('cache_res.pkl','wb'))
# validation
times=[r[0] for r in res]
assert len(set(times))==len(times)==len(dates)
assert all(t==d for t,d in zip(times,dates))
LAT=res[0][2]; LON=res[0][3]
assert all(np.array_equal(r[2],LAT) and np.array_equal(r[3],LON) for r in res)
print(set(r[4] for r in res), LAT.shape, LON.shape, LAT[[0,-1]], LON[[0,-1]])
X=np.stack([r[1] for r in res])  # (T,lat,lon)
print(X.shape)
bl_mask=(dates<=pd.Timestamp('2003-01-05'))&(dates>=pd.Timestamp('1991-12-27'))
tg_mask=(dates>=pd.Timestamp('2021-06-01'))&(dates<=pd.Timestamp('2021-08-31'))
print(bl_mask.sum(), tg_mask.sum())
Xt=X[tg_mask]; tdates=dates[tg_mask]
sea=np.all(np.isfinite(Xt),axis=0)
print('sea cells', sea.sum(), 'of', sea.size, 'target days', len(tdates))
print('partial NaN cells in target', (np.isfinite(Xt).any(0) & ~sea).sum())
print('baseline NaN frac among sea cells', np.isnan(X[bl_mask][:,sea]).mean())
print('value range', np.nanmin(Xt), np.nanmax(Xt), 'min/max loaded', np.nanmin(X), np.nanmax(X))
