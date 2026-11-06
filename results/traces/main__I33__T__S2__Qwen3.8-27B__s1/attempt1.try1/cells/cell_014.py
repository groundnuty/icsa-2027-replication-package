import numpy as np
mask = np.load('/tmp/mask_flat.npy')   # (92, 3600)
sea = np.load('/tmp/sea.npy')
tdates = np.load('/tmp/tdates.npy')
active = mask.any(axis=1)

# daily active cell counts around boundaries
for i in list(range(33, 42)) + list(range(72, 92)):
    print(tdates[i], 'active cells:', int(mask[i, sea].sum()), 'active:', bool(active[i]))

# check a sample cell's hot sequence and its MHWs
c = int(np.nonzero(mask[40].sum() if False else mask[:, :].sum(axis=0))[0])
col = mask[:, c]
print('sample cell idx', c, 'mhw days:', int(col.sum()), 'span', int(np.nonzero(col)[0].min()), '-', int(np.nonzero(col)[0].max()))

# verify quantile method behavior
q = np.quantile(np.arange(121, dtype=float), 0.9, method='hazen')
print('hazen q0.9 of 0..120 =', q, '(expect 108.0)')
q2 = np.quantile(np.arange(120, dtype=float), 0.9, method='hazen')
print('hazen q0.9 of 0..119 =', q2, '(expect 107.1)')
