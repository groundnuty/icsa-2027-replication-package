import numpy as np, h5py
d = '/data/icsa2027_data_20261101T090944Z/s1z'
# hunt: where do the two reads of 20030810 differ?
def read_sub(datestr):
    with h5py.File(f'{d}/sst_{datestr}.nc', 'r') as f:
        return f['analysed_sst'][0, 196:256, 485:545]
r1 = read_sub('20030810'); r2 = read_sub('20030810')
neq = (r1 != r2) & ~(np.isnan(r1) & np.isnan(r2))
print('cells differing (treating nan==nan):', neq.sum())
if neq.sum():
    idx = np.argwhere(neq)
    for i, j in idx[:10]:
        print('cell', i, j, r1[i, j], r2[i, j])
    # also check NaN vs value mismatch
    print('nan1 XOR nan2 count:', (np.isnan(r1) ^ np.isnan(r2)).sum())
else:
    # fully identical with nan==nan; the earlier array_equal 'False' came from NaN-aware comparison
    print('so difference is only in NaN==NaN handling')
    print('np.array_equal with equal_nan:', np.array_equal(r1, r2, equal_nan=True))
