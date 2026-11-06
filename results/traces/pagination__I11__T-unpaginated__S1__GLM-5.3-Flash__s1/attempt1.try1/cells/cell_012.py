import numpy as np, json, time
raw_thresh = np.load('cache/raw_thresh.npy'); raw_clim = np.load('cache/raw_clim.npy')
sm_t = np.load('cache/sm_thresh.npy'); sm_c = np.load('cache/sm_clim.npy')  # direct method (saved)
tgt = np.load('cache/tgt.npy')
sea = np.isfinite(tgt).all(axis=0)

def smooth_cumsum(a):
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.cumsum(pad, axis=0); c = np.concatenate([np.zeros_like(c[:1]), c], axis=0)
    return (c[31:] - c[:-31]) / 31.0

for name, arr, sm in [('thresh', raw_thresh, sm_t), ('clim', raw_clim, sm_c)]:
    s1 = smooth_cumsum(arr)
    d = (s1 - sm)[:, sea]
    print('%s: cumsum vs direct on sea cells: max|diff| = %.3e K, n(diff!=0) = %d of %d'
          % (name, np.abs(d).max(), int((d != 0).sum()), d.size))
    # manual window verification on sea cells only
    pad = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    ok = True
    for i in [0, 1, 59, 100, 182, 243, 300, 350, 365]:
        m = pad[i:i+31].mean(axis=0)[sea]
        if not np.array_equal(m, sm[i][sea]):
            ok = False; print('  mismatch at day', i+1, np.abs(m - sm[i][sea]).max())
    print('  direct == manual 31-day window mean (sea cells) at all probes:', ok)

# does the ~1e-13 difference matter for the hot-day mask?
hot_direct = tgt >= sm_t          # (92,60,60)
hot_cumsum = tgt >= smooth_cumsum(raw_thresh)
print('hot-day mask identical (direct vs cumsum):', bool((hot_direct == hot_cumsum).all()))
nflip = int((hot_direct != hot_cumsum).sum()); print('flipped cells-days:', nflip)
# how close is any SST to its threshold? (tie risk check)
diffs = (tgt - sm_t)[:, sea]
print('min |SST - thresh| over sea cells: %.6f K' % np.abs(diffs).min())
print('n |SST-thresh| < 1e-9:', int((np.abs(diffs) < 1e-9).sum()), '| n exactly equal:', int((diffs == 0).sum()))
print('total hot cell-days (direct):', int(hot_direct.sum()))
