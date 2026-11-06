import numpy as np, xarray as xr, h5py, time, os
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
t0=time.time()
with h5py.File(p,'r') as f:
    print('h5 vars:', list(f.keys()))
    dset = f['analysed_sst']
    print('chunks', dset.chunks, 'compression', dset.compression, 'fillvalue', dset.fillvalue)
    # smoke test: 3 days
    sub = dset[13665:13668, 551:611, 649:709]
    print('smoke', sub.shape, sub.dtype, 'finite frac', np.isfinite(sub).mean(), 't', time.time()-t0)
    base = dset[3647:7675, 551:611, 649:709]
    print('base read', base.shape, time.time()-t0)
    tgt  = dset[13665:13757, 551:611, 649:709]
    print('tgt read', tgt.shape, time.time()-t0)
np.save('/tmp/base.npy', base)
np.save('/tmp/tgt.npy', tgt)
print('saved', time.time()-t0)
print('base finite frac', np.isfinite(base).mean(), 'tgt finite frac', np.isfinite(tgt).mean())
sea = np.isfinite(tgt).all(axis=0)
print('sea cells', int(sea.sum()), 'of', tgt[0].size)
print('base per-day finite frac: min', np.isfinite(base).mean(axis=(1,2)).min(), 'max', np.isfinite(base).mean(axis=(1,2)).max())
# check all target days fully finite exactly on sea cells
allfin = np.isfinite(tgt).all(axis=0)
print('cells finite on all 92 days:', int(allfin.sum()))
print('any cell finite on some but not all days:', int((np.isfinite(tgt).any(axis=0) & ~allfin).sum()))
print('tgt range on sea cells: %.3f %.3f K' % (tgt[:, allfin].min(), tgt[:, allfin].max()))
print('base range on sea cells: %.3f %.3f K' % (base[:, allfin].min(), base[:, allfin].max()))
print('base NaN cells (any NaN over baseline):', int((~np.isfinite(base)).any(axis=0).sum()))
print('sample sst 2019-06-01 cell(0,0):', tgt[0,0,0], ' cell(30,30):', tgt[0,30,30])
