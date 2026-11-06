import numpy as np, datetime as dt

datestrs = np.load('/work/extract_dates.npy')
arr32 = np.load('/work/extract_sst.npy')
dates = [dt.date.fromisoformat(s) for s in datestrs]
n_base_win = sum(1 for d in dates if d <= dt.date(2003,1,5))
tgt_dates = dates[n_base_win:]
thr_s3 = np.load('/work/thr_s.npy')   # (366, 60, 60)
clim_s3 = np.load('/work/clim_s.npy')

sst_t = arr32[n_base_win:].astype(np.float64)   # (92, 60, 60)
print('target days:', sst_t.shape)

# step 1: sea cells = finite on every target day
finite_all = np.isfinite(sst_t).all(axis=0)     # (60,60)
sea = finite_all
print('sea cells:', int(sea.sum()), 'land:', int((~sea).sum()))
# cross-check vs baseline finiteness
finite_base = np.isfinite(arr32[:n_base_win].astype(np.float64)).all(axis=0)
print('baseline-finite cells:', int(finite_base.sum()))
print('sea == baseline-finite:', np.array_equal(sea, finite_base))
# any cell finite in target but not baseline or vice versa
print('target-finite only:', int((finite_all & ~finite_base).sum()), 'base-finite only:', int((finite_base & ~finite_all).sum()))
# count target days with any NaN in sea cells
nan_per_day = (~np.isfinite(sst_t)).sum(axis=(1,2))
print('days with any NaN in region:', int((nan_per_day>0).sum()))
# do these NaNs occur only in land cells?
land_nan_ok = True
for i in range(sst_t.shape[0]):
    m = np.isnan(sst_t[i])
    if (m & sea).any():
        land_nan_ok = False
        print('NaN in sea cell on', tgt_dates[i], int((m&sea).sum()))
        break
print('all NaNs confined to land cells:', land_nan_ok)
np.save('/work/sea_mask.npy', sea)
