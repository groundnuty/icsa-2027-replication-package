import numpy as np
z = np.load('/work/doy_stats.npz')
rt = z['raw_thresh']
nanper = np.isnan(rt).sum(axis=1)
odd = np.where(nanper != 286)[0]
print("days with NaN count != 286:", [(i+1, int(nanper[i])) for i in odd])
# look at a specific sea cell column: find one
finite_all = np.all(np.isfinite(rt), axis=0)
print("cells finite all 366 days:", finite_all.sum(), "(expect 3314)")
print("sample finite cell values day 1..5:", rt[:5, :3000][np.isfinite(rt[:5,:3000]).all(0)][0][:5] if finite_all[:3000].any() else None)
# check which cell is finite
col = np.where(finite_all)[0][0]
print("cell", col, "values for days 58..62:", rt[57:63, col])
# and raw day 58/60 for that cell
print("finite fraction of each day (col sample):", np.isfinite(rt[:, :200]).mean(axis=1)[:10])
