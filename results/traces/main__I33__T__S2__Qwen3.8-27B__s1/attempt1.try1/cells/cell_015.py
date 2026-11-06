import numpy as np
mask = np.load('/tmp/mask_flat.npy')
sea = np.load('/tmp/sea.npy')
tdates = np.load('/tmp/tdates.npy')
tgt = np.load('/tmp/sst_target.npy').reshape(92, -1)
thr_s = np.load('/tmp/thr_s.npy')
tdoy = np.load('/tmp/tdoy.npy')
active = mask.any(axis=1)
for i in range(46, 51):
    print(tdates[i], 'active cells:', int(mask[i, sea].sum()))

q = np.quantile(np.arange(121, dtype=float), 0.9, method='hazen')
q2 = np.quantile(np.arange(120, dtype=float), 0.9, method='hazen')
print('hazen q0.9 of 0..120 =', q, '(expect 108.0); 0..119 =', q2, '(expect 107.1)')

# sample cell with an MHW
counts = mask.sum(axis=0)
c = int(np.argmax(counts[sea]))
# show its hot vs mhw pattern in a window
hot_c = tgt[:, c] >= thr_s[tdoy-1, c]
h = ''.join('H' if x else '.' for x in hot_c)
m = ''.join('M' if x else '.' for x in mask[:, c])
print('cell', c, 'count', int(counts[c]))
print('hot:', h)
print('mhw:', m)
