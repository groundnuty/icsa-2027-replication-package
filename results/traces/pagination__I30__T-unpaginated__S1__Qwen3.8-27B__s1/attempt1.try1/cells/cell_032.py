
import sys, numpy as np
sys.path.insert(0,'/work/mhw')
sea = np.load('/work/mhw/sea.npy')
thr_s = np.load('/work/mhw/thr_s.npy')
doy_tgt = np.load('/work/mhw/doy_tgt.npy')
import common
ext, tgt, done = common.load_state()
S = tgt.astype(np.float64)
hot = (S.T >= thr_s[:, doy_tgt]); hot[~sea, :] = False

for c in (0, 1, 2):
    print('cell', c, 'hot:', ''.join('H' if v else '.' for v in hot[c]))
    print('cell', c, 'mask:', ''.join('M' if v else '.' for v in np.load('/work/mhw/mask.npy')[:, c]))
    # show SST - threshold margin around idx 28..50
    thr_t = thr_s[c, doy_tgt]
    mar = S[:, c] - thr_t
    print('   margins idx28-50:', np.round(mar[28:50], 2))
