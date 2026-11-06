import numpy as np, time

coords = np.load('/work/coords.npz', allow_pickle=True)
time_ext = coords['time_ext']; time_tgt = coords['time_tgt']
sst64 = np.load('/work/sst_ext.npy').astype(np.float64)
tgt64 = np.load('/work/sst_tgt.npy').astype(np.float64)
sea = np.all(np.isfinite(tgt64), axis=0)
thr_raw = np.load('/work/thr_raw.npy'); clim_raw = np.load('/work/clim_raw.npy')

# where are the NaNs? per-doy-row NaN cell counts
nan_per_row = np.isnan(thr_raw).sum(axis=(1,2))
print('rows with NaN:', int((nan_per_row>0).sum()), '| min/max NaNs per NaN row:', int(nan_per_row[nan_per_row>0].min()), int(nan_per_row.max()))
# are NaN cells the same across rows? and do they match cells with NaN in ext data?
nan_cells = np.isnan(thr_raw).any(axis=0)
print('cells with any NaN thr:', int(nan_cells.sum()))
same = np.all(np.isnan(thr_raw) == np.isnan(thr_raw[0:1]), axis=0)
print('same NaN pattern across all 366 rows:', bool(same.all()))
ext_nan_cells = np.any(~np.isfinite(sst64), axis=0)
print('cells with any NaN in ext block:', int(ext_nan_cells.sum()), '| identical sets:', bool(np.array_equal(nan_cells, ext_nan_cells)))
# NaNs among sea cells?
print('NaN thr among sea cells:', int((nan_cells & sea).sum()))
print('any NaN in thr among sea cells anywhere:', int(np.isnan(thr_raw[:, sea]).sum()))
print('any NaN in clim among sea cells anywhere:', int(np.isnan(clim_raw[:, sea]).sum()))
