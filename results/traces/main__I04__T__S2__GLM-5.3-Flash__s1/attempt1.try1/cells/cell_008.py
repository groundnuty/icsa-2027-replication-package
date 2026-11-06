import numpy as np, warnings

win = np.load('/tmp/win.npy')      # float32 (4028,60,60), 1991-12-27..2003-01-05
wd  = np.load('/tmp/dates.npy')[3647:7675]
tgt = np.load('/tmp/tgt.npy')      # float64 (92,60,60), 2020-06-01..2020-08-31

# constant NaN mask?
nanw = np.isnan(win)   # (4028,60,60)
same_all = np.all(nanw == nanw[0])
nant = np.isnan(tgt)
same_t = np.all(nant == nanw[0])
print('window NaN pattern constant across days:', same_all)
print('target NaN pattern == window pattern:', same_t)
n_land = int(nanw[0].sum())
print('land cells:', n_land, 'of', 60*60)
# any cell: NaN in target but finite somewhere in window or vice versa?
finite_all_w = np.all(np.isfinite(win), axis=0)
finite_all_t = np.all(np.isfinite(tgt), axis=0)
print('cells finite all target days:', int(finite_all_t.sum()))
print('cells finite all window days:', int(finite_all_w.sum()))
print('finite-all-window == finite-all-target:', np.array_equal(finite_all_w, finite_all_t))
np.save('/tmp/finite_all_t.npy', finite_all_t)
