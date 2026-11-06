import numpy as np, pickle

a = np.load('/tmp/base_a.npz'); b = np.load('/tmp/base_b.npz'); t = np.load('/tmp/tgt.npz')
base = np.concatenate([a['arr'], b['arr']], axis=0)
bdates = np.concatenate([a['dates'], b['dates']])
base_times = np.concatenate([a['times'], b['times']])
tgt = t['arr']; tdates = t['dates']; ttimes = t['times']

print('base shape', base.shape, bdates[0], '->', bdates[-1])
print('tgt shape', tgt.shape, tdates[0], '->', tdates[-1])
# contiguity check
import datetime as dt
d = [dt.date.fromisoformat(x) for x in bdates]
gaps = [d[i+1]-d[i] for i in range(len(d)-1)]
print('base contiguous:', all(g==dt.timedelta(days=1) for g in gaps))
d2 = [dt.date.fromisoformat(x) for x in tdates]
print('tgt contiguous:', all(d2[i+1]-d2[i]==dt.timedelta(days=1) for i in range(len(d2)-1)))
print('times match dates:', np.array_equal(base_times.astype('datetime64[D]').astype(str)[:, :10], bdates),
      np.array_equal(ttimes.astype('datetime64[D]').astype(str)[:, :10], tdates))

finite_tgt = np.all(np.isfinite(tgt), axis=0)
print('sea cells (finite all 92 target days):', int(finite_tgt.sum()), 'of', finite_tgt.size)
land = ~finite_tgt
print('land cells:', int(land.sum()))
# where are land cells
ys, xs = np.where(land)
latv = np.load('/tmp/region_meta.pkl', allow_pickle=True)
print('land lat/lon examples:', sorted(set(zip(ys.tolist(), xs.tolist())))[:20])

nan_base = ~np.isfinite(base)
print('baseline NaN fraction overall:', float(nan_base.mean()))
nan_per_cell_base = nan_base.sum(axis=0)
print('cells with >=1 baseline NaN:', int((nan_per_cell_base>0).sum()), 'max NaN days in a cell:', int(nan_per_cell_base.max()))
sea_cells = np.where(finite_tgt)[0]
print('sea cells with >=1 baseline NaN:', int((nan_per_cell_base[sea_cells]>0).sum()))
print('sea cells with all baseline finite:', int((nan_per_cell_base[sea_cells]==0).sum()))