import numpy as np
z = np.load('/work/doy_stats.npz')
rt, rc = z['raw_thresh'], z['raw_clim']
st, sc = z['sm_thresh'], z['sm_clim']
finite_all = np.all(np.isfinite(rt), axis=0)
sea = np.where(finite_all)[0]
print("n sea:", len(sea))
print("raw thr sea range:", rt[:, sea].min(), rt[:, sea].max())
print("raw clim sea range:", rc[:, sea].min(), rc[:, sea].max())
print("sm thr sea range:", st[:, sea].min(), st[:, sea].max())
print("sm clim sea range:", sc[:, sea].min(), sc[:, sea].max())
print("sm thr finite frac:", np.isfinite(st).mean())
# manual check for one sea cell, several days
col = sea[0]
for d in [1, 60, 153, 366]:
    idx = [(d-16+i) % 366 for i in range(31)]
    manual = rt[idx, col].mean()
    print("d=", d, "manual:", manual, "computed:", st[d-1, col], "diff:", abs(st[d-1,col]-manual))
# print a sample of raw thresholds for that cell across the target doys
td = z['target_doy']
print("target doys:", td.min(), td.max())
print("raw thr sea cell days 150..160:", rt[149:160, col].round(4))
print("sm thr sea cell days 150..160:", st[149:160, col].round(4))
