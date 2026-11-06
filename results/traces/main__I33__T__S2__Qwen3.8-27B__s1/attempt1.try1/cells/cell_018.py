import numpy as np
mask = np.load('/tmp/mask_flat.npy')
col = mask[:, 2299].astype(bool)
print(col.astype(int))
pad = np.concatenate(([0], col.view(np.int8), [0]))
d = np.diff(pad)
print('diff', d)
s = np.nonzero(d==1)[0]; e = np.nonzero(d==-1)[0]-1
print('s', s, 'e', e)
print('durs', [int(x-y+1) for x,y in zip(s,e)])
