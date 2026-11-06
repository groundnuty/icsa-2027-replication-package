import numpy as np, datetime as dt, json
tgt = np.load('cache/tgt.npy')
meta = json.load(open('cache/meta.json'))
dates_tgt = [dt.date.fromisoformat(s) for s in meta['dates_tgt']]
raw_thresh = np.load('cache/raw_thresh.npy'); raw_clim = np.load('cache/raw_clim.npy')
sm_t = np.load('cache/sm_thresh.npy'); sm_c = np.load('cache/sm_clim.npy')
sea = np.isfinite(tgt).all(axis=0)

cum = np.concatenate([[0], np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])])
def md_doy(d): return int(cum[d.month-1] + d.day)
tgt_doys = np.array([md_doy(d) for d in dates_tgt])
print('target doys: first', tgt_doys[0], 'last', tgt_doys[-1], 'unique span:', len(set(tgt_doys)))

def smooth_cumsum(a):
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.cumsum(pad, axis=0); c = np.concatenate([np.zeros_like(c[:1]), c], axis=0)
    return (c[31:] - c[:-31]) / 31.0

hot_direct = tgt >= sm_t[tgt_doys]
hot_cumsum = tgt >= smooth_cumsum(raw_thresh)[tgt_doys]
print('hot-day mask identical (direct vs cumsum smoothing):', bool((hot_direct == hot_cumsum).all()))
print('total hot cell-days:', int(hot_direct.sum()))
diffs = (tgt - sm_t[tgt_doys])[:, sea]
print('min |SST - thresh| on sea cells: %.6f K | exact ties: %d | within 1e-9: %d'
      % (np.abs(diffs).min(), int((diffs == 0).sum()), int((np.abs(diffs) < 1e-9).sum())))
# also verify target climatology side is consistent
print('mean SST-smoothclim (sea) during period: %.3f K' % (tgt - sm_c[tgt_doys])[:, sea].mean())
# hot-day counts per day (first/last few)
hd = hot_direct.reshape(92, -1).sum(axis=1)
print('hot cells per day (first 10):', hd[:10].tolist())
print('hot cells per day (last 10):', hd[-10:].tolist())
print('max hot cells in a day:', int(hd.max()), 'at index', int(hd.argmax()), dates_tgt[int(hd.argmax())])
np.save('cache/hot.npy', hot_direct)
