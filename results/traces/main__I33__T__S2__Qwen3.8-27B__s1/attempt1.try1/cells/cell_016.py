import numpy as np
mask = np.load('/tmp/mask_flat.npy')
sea = np.load('/tmp/sea.npy')
active = mask.any(axis=1)
tot = 92*3290
print('membership fraction:', mask.sum(axis=0)[sea].sum()/tot)
print('daily active cells:', [int(x) for x in active.sum(axis=1)])
# distribution of per-cell MHW durations
durs = []
for c in np.nonzero(sea)[0]:
    col = mask[:, c].astype(bool)
    d = np.diff(np.concatenate(([0], col.view(np.int8), [0])))
    s = np.nonzero(d==1)[0]; e = np.nonzero(d==-1)[0]-1
    durs.extend((x-y+1) for x,y in zip(s,e))
import collections
print('n cell-MHWs:', len(durs), 'min/max dur:', min(durs), max(durs))
print('duration dist:', dict(sorted(collections.Counter(durs).items())))
