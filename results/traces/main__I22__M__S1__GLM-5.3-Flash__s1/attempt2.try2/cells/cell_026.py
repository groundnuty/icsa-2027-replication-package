import numpy as np, h5py
d = '/data/icsa2027_data_20261101T090944Z/s1z'
def read_sub(datestr):
    with h5py.File(f'{d}/sst_{datestr}.nc', 'r') as f:
        return f['analysed_sst'][0, 196:256, 485:545]
r1 = read_sub('20030810'); r2 = read_sub('20030810')
nan1 = np.isnan(r1); nan2 = np.isnan(r2)
print('nan equal:', np.array_equal(nan1, nan2), '| both same count:', nan1.sum(), nan2.sum())
if not np.array_equal(r1[~nan1], r2[~nan1]):
    diff = np.abs(r1[~nan1].astype(np.float64) - r2[~nan1].astype(np.float64))
    print('valid-value diffs: max', diff.max(), 'n nonzero', (diff > 0).sum())
# check bitwise
x1 = r1[~nan1].view(np.uint32); x2 = r2[~nan1].view(np.uint32)
print('bitwise equal:', np.array_equal(x1, x2), '| n differing bits:', (x1 != x2).sum(), 'of', x1.size)
print('example:', r1[~nan1][:5], r2[~nan1][:5])
