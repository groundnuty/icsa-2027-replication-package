import h5py, numpy as np
f = h5py.File('/work/sst_s2.nc','r')
d = f['analysed_sst']
print('chunks:', d.chunks, 'compression:', d.compression, 'comp_opts:', d.compression_opts, 'shuffle:', d.shuffle)
print('dtype:', d.dtype, 'shape:', d.shape)
print('attrs:', dict(d.attrs))
for k in ['time','latitude','longitude']:
    print(k, dict(f[k].attrs) if k in f else None)
import sys
sys.stdout.flush()
# sample a small slab to check units/fill
import numpy as np
sub = d[0:5, 300:310, 50:60]
print('sample min/max/mean:', np.nanmin(sub), np.nanmax(sub), np.nanmean(sub), 'nan count', np.isnan(sub).sum(), 'of', sub.size)
print('global attrs sample:', {k: f.attrs[k] for k in list(f.attrs)[:8]})
f.close()
