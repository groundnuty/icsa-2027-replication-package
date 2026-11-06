import numpy as np, collections
mask = np.load('/tmp/mask_flat.npy')
sea = np.load('/tmp/sea.npy')
tdates = np.load('/tmp/tdates.npy')
acount = mask[:, sea].sum(axis=1)
print('daily active cells:', [int(x) for x in acount])
durs = []
for c in np.nonzero(sea)[0]:
    col = mask[:, c].astype(bool)
    d = np.diff(np.concatenate(([0], col.view(np.int8), [0])))
    s = np.nonzero(d==1)[0]; e = np.nonzero(d==-1)[0]-1
    durs.extend(int(x-y+1) for x,y in zip(s,e))
print('n cell-MHWs:', len(durs), 'min/max dur:', min(durs), max(durs))
print('duration dist:', dict(sorted(collections.Counter(durs).items())))
