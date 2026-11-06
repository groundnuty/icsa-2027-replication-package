import numpy as np
z = np.load('/work/sst_region.npz', allow_pickle=False)
A = z['A']; dates = [str(d) for d in z['dates']]
d2i = {d: i for i, d in enumerate(dates)}
ext_n = d2i['2003-01-05'] + 1
ext = A[:ext_n]

fin_ext = np.all(np.isfinite(ext), axis=0)   # (60,60)
missing = ~fin_ext
print("cells with any NaN in ext period:", missing.sum())
per_day = (~np.isfinite(ext)).sum(axis=(1,2))
print("per-day NaN counts min/max over ext:", per_day.min(), per_day.max())
tgt = A[d2i['2010-06-01']:d2i['2010-08-31']+1]
fin_tgt = np.all(np.isfinite(tgt), axis=0)
sea = fin_tgt
print("target per-day NaN min/max:", (~np.isfinite(tgt)).sum(axis=(1,2)).min(), (~np.isfinite(tgt)).sum(axis=(1,2)).max())
print("sea cells:", sea.sum(), "non-sea:", (~sea).sum())
print("non-sea & missing in ext:", ((~sea) & missing).sum())
print("sea cells with any ext NaN:", (sea & missing).sum())

tc = np.load('/work/thr_cli.npz', allow_pickle=False)
thr, cli = tc['thr'], tc['cli']
land_cells = np.argwhere(~sea)
c0 = land_cells[0]
print("sample non-sea cell idx:", c0)
print("thr NaN d's for it:", np.isnan(thr[1:, c0[0], c0[1]]).sum(), " cli NaN d's:", np.isnan(cli[1:, c0[0], c0[1]]).sum())
print("cli values:", cli[[153,200], c0[0], c0[1]])
print("thr NaN total:", np.isnan(thr[1:]).sum(), " cli NaN total:", np.isnan(cli[1:]).sum())
