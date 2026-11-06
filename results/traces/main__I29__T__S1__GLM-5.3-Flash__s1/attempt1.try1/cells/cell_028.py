import numpy as np, datetime

doy_ext = np.load('doy_ext.npy')
base_ext = np.load('base_ext.npy')

# Build index lists per doy: for doy d (1..366, d != 60), pool = all days with |doy - d| <= 5
idx_lists = {}
for d in range(1, 367):
    if d == 60:
        continue
    sel = np.where(np.abs(doy_ext.astype(int) - d) <= 5)[0]
    idx_lists[d] = sel

# verify a few
print('doy 1 pool doys:', sorted(set(doy_ext[idx_lists[1]].tolist())))
print('doy 60 would-be pool doys:', sorted(set(doy_ext[np.where(np.abs(doy_ext.astype(int)-60)<=5)[0]].tolist())))
print('doy 366 pool doys:', sorted(set(doy_ext[idx_lists[366]].tolist())))
print('doy 100 pool size', len(idx_lists[100]), 'doy 1 pool size', len(idx_lists[1]))
# every doy 1..366 except 60 has a nonempty pool?
print('all pools nonempty:', all(len(idx_lists[d])>0 for d in range(1,367) if d!=60))
# distribution of pool sizes
sizes = [len(idx_lists[d]) for d in range(1,367) if d!=60]
print('pool size min/max:', min(sizes), max(sizes))
