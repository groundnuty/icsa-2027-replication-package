import numpy as np, datetime
hot = np.load('hot.npy')
# verify: max run of consecutive hot days per cell
def max_run(mask2d_time):
    best = 0
    for i in range(mask2d_time.shape[1]):
        for j in range(mask2d_time.shape[2]):
            col = mask2d_time[:,i,j]
            if not col.any(): continue
            # run lengths
            d = np.diff(np.concatenate([[0], col.view(np.int8), [0]]))
            starts = np.where(d==1)[0]; ends = np.where(d==-1)[0]
            best = max(best, int((ends-starts).max()))
    return best
mr = max_run(hot)
print('max consecutive hot run over all cells:', mr)
# count cells with any run >=5
def has_run5(col):
    c = col.view(np.int8)
    d = np.diff(np.concatenate([[0], c, [0]]))
    starts = np.where(d==1)[0]; ends = np.where(d==-1)[0]
    return ((ends-starts)>=5).any()
cells_with_runs = 0
for i in range(60):
    for j in range(60):
        if hot[:,i,j].any() and has_run5(hot[:,i,j]):
            cells_with_runs += 1
print('cells with any >=5-day hot run:', cells_with_runs)
