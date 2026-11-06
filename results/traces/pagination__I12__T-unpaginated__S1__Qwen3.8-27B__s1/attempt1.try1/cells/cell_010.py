import numpy as np, pickle, datetime as dt

a = np.load('/tmp/base_a.npz'); b = np.load('/tmp/base_b.npz'); t = np.load('/tmp/tgt.npz')
base = np.concatenate([a['arr'], b['arr']], axis=0)
bdates = np.concatenate([a['dates'], b['dates']])
base_times = np.concatenate([a['times'], b['times']])
tgt = t['arr']; tdates = t['dates']; ttimes = t['times']

td = [s[:10] for s in base_times.astype('datetime64[D]').astype(str)]
print('base times match dates:', np.array_equal(np.array(td), bdates))
td2 = [s[:10] for s in ttimes.astype('datetime64[D]').astype(str)]
print('tgt times match dates:', np.array_equal(np.array(td2), tdates))

finite_tgt = np.all(np.isfinite(tgt), axis=0)
print('sea cells (finite all 92 target days):', int(finite_tgt.sum()), 'of', finite_tgt.size)
land = ~finite_tgt
print('land cells:', int(land.sum()))
ys, xs = np.where(land)
print('n land coords:', len(ys), 'examples:', list(zip(ys.tolist(), xs.tolist()))[:10])

nan_base = ~np.isfinite(base)
print('baseline NaN fraction overall:', float(nan_base.mean()))
nan_per_cell_base = nan_base.sum(axis=0)
print('cells with >=1 baseline NaN:', int((nan_per_cell_base>0).sum()), 'max NaN days in a cell:', int(nan_per_cell_base.max()))
sea_cells = np.where(finite_tgt)[0]
print('sea cells with >=1 baseline NaN:', int((nan_per_cell_base[sea_cells]>0).sum()))
print('sea cells with all baseline finite:', int((nan_per_cell_base[sea_cells]==0).sum()))
# land cell baseline NaNs
print('land cells all-NaN in baseline:', int((nan_per_cell_base[land]==base.shape[0]).sum()))