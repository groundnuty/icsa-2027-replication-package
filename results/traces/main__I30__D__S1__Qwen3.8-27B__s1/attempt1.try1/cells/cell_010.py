import numpy as np
z = np.load('/work/sst_region.npz', allow_pickle=False)
A = z['A']; dates = [str(d) for d in z['dates']]
d2i = {d: i for i, d in enumerate(dates)}
ext_n = d2i['2003-01-05'] + 1
ext = A[:ext_n]

# which cells are NaN somewhere in ext period?
fin_ext = np.isfinite(ext, axis=0)   # (4028,60,60)
missing = ~fin_ext.all(axis=0)       # cells with >=1 NaN in ext
print("cells with any NaN in ext period:", missing.sum())
# per-day missing counts over ext
per_day = (~fin_ext).sum(axis=(1,2))
print("per-day NaN counts min/max over ext:", per_day.min(), per_day.max())
# target period
tgt = A[d2i['2010-06-01']:d2i['2010-08-31']+1]
fin_tgt = np.isfinite(tgt, axis=0)
sea = fin_tgt.all(axis=0)
print("target period: per-day NaN min/max:", (~fin_tgt).sum(axis=(1,2)).min(), (~fin_tgt).sum(axis=(1,2)).max())
print("sea cells (finite all 92 target days):", sea.sum(), " land/missing:", (~sea).sum())
print("overlap: cells missing in ext but sea in target:", (missing & sea).sum())
print("sea cells with any ext-period NaN:", (sea & missing).sum())

tc = np.load('/work/thr_cli.npz', allow_pickle=False)
thr, cli = tc['thr'], tc['cli']
# for a land cell, check
land_cells = np.argwhere(~sea)
print("sample land cell:", land_cells[0])
c0 = land_cells[0]
print("thr NaN count for that cell over d:", np.isnan(thr[1:, c0[0], c0[1]]).sum())
print("cli NaN count for that cell over d:", np.isnan(cli[1:, c0[0], c0[1]]).sum())
print("cli sample values:", cli[[153,200], c0[0], c0[1]])
print("thr NaN total:", np.isnan(thr[1:]).sum(), "cli NaN total:", np.isnan(cli[1:]).sum())
