import numpy as np
z = np.load('data/climthr.npz')
thr_smooth = z['thr_smooth']; clim_smooth = z['clim_smooth']; sea = z['sea']; tgt_doy = z['tgt_doy']

# NaNs in smoothed threshold
nanmap = ~np.isfinite(thr_smooth)  # (366, 60, 60)
nan_per_cell = nanmap.sum(axis=0)  # (60,60)
print('cells with any NaN smoothed thr:', (nan_per_cell>0).sum())
print('cells with NaNs (land):', ((nan_per_cell>0) & ~sea).sum())
print('sea cells with any NaN smoothed thr:', ((nan_per_cell>0) & sea).sum())
# among sea cells: NaNs restricted to target doys
tgt_slice = nanmap[tgt_doy-1]  # (92, 60, 60)
sea_nan_tgt = (tgt_slice.sum(axis=0) > 0) & sea
print('sea cells with NaN thr in any target doy:', sea_nan_tgt.sum())
print('sea cells fully finite over target doys:', ((tgt_slice.sum(axis=0)==0) & sea).sum())
# worst case: how many target-doy NaNs per sea cell
vals = tgt_slice.sum(axis=0)[sea]
print('distribution of NaN target-doy count among sea cells:', dict(zip(*np.unique(vals, return_counts=True))))
# check raw pools NaN extent for sea cells
thr_raw = z['thr_raw']
raw_nan = (~np.isfinite(thr_raw)).sum(axis=0)[sea]
print('raw thr NaN doy counts among sea cells:', dict(zip(*np.unique(raw_nan, return_counts=True))))