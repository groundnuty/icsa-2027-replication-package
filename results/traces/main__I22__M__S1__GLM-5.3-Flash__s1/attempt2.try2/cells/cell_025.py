import numpy as np, h5py, datetime as dt
d = '/data/icsa2027_data_20261101T090944Z/s1z'
def read_sub(datestr):
    with h5py.File(f'{d}/sst_{datestr}.nc', 'r') as f:
        return f['analysed_sst'][0, 196:256, 485:545]
a = read_sub('20030810'); b = read_sub('20030810')
print('same file, two reads identical:', np.array_equal(a, b))
# find a differing pair from the parallel-vs-sequential test set
import itertools
dates = [f'200308{dd:02d}' for dd in range(1, 32)]
diffs = []
for ds in dates[:8]:
    r1 = read_sub(ds); r2 = read_sub(ds)
    if not np.array_equal(r1, r2):
        # NaN pattern differs?
        nan1 = np.isnan(r1); nan2 = np.isnan(r2)
        print(ds, 'nan pattern equal:', np.array_equal(nan1, nan2),
              '| valid vals equal:', np.array_equal(r1[~nan1], r2[~nan1]) if nan1.sum()==nan2.sum() else 'n/a')
