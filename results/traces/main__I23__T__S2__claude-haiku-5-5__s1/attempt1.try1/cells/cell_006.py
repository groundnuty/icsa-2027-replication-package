
import os, json
os.makedirs('output', exist_ok=True)
# date-indexed baseline SST (1991-12-27..2003-01-05)
bt = pd.DatetimeIndex(base.time.values)
bvals = base.values.astype(np.float64)
def doy(ts):
    return np.array([pd.Timestamp(2000, t.month, t.day).dayofyear for t in ts])
bdoy = doy(bt)
# baseline anchor dates: 1992-01-01..2002-12-31
anchor = bt[(bt>=pd.Timestamp('1992-01-01'))&(bt<=pd.Timestamp('2002-12-31'))]
adoy = doy(anchor)
ncell = bvals.shape[1]*bvals.shape[2]
thr = np.full((367,)+bvals.shape[1:], np.nan)
clim = np.full((367,)+bvals.shape[1:], np.nan)
for d in range(1,367):
    if d==60: continue
    anc = anchor[adoy==d]
    if len(anc)==0: continue
    mask = np.zeros(len(bt),bool)
    for b in anc:
        mask |= np.abs((bt-b).days)<=5
    pool = bvals[mask]
    thr[d] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    clim[d] = np.nanmean(pool, axis=0)
print("days filled:", np.sum(~np.isnan(thr[1:,0,0])))
