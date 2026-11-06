import numpy as np, pandas as pd

z = np.load("work/data.npz")
base = z["base"].astype(np.float64); targ = z["targ"].astype(np.float64)
nb, nt = base.shape[0], targ.shape[0]

fin_base = np.isfinite(base)          # (4028, 60, 60)
fin_targ = np.isfinite(targ)          # (92, 60, 60)

# is the finite set constant across days?
cnt_base = fin_base.reshape(nb, -1).sum(1)
cnt_targ = fin_targ.reshape(nt, -1).sum(1)
print("base finite/day:", cnt_base.min(), cnt_base.max())
print("targ finite/day:", cnt_targ.min(), cnt_targ.max())

m01 = fin_base[0]; mdiff = [(i, (fin_base[i] != m01).sum()) for i in range(0, nb, 500)]
print("days where finite set differs from day0 (sampled):", [(i, d) for i, d in mdiff if d > 0])
any_diff = np.array([(fin_base[i] != m01).any() for i in range(nb)])
print("base days with differing finite set:", any_diff.sum(), "of", nb)
any_diff_t = np.array([(fin_targ[i] != fin_targ[0]).any() for i in range(nt)])
print("targ days with differing finite set:", any_diff_t.sum(), "of", nt)

# per-cell finite counts
cnt_cell_base = fin_base.sum(0)
cnt_cell_targ = fin_targ.sum(0)
sea_targ = cnt_cell_targ == nt
print("cells finite all target days (sea cells):", sea_targ.sum())
print("cells never finite:", (cnt_cell_base == 0).sum())
import collections
print("base per-cell finite count distribution:", dict(collections.Counter(cnt_cell_base.ravel().tolist())))
print("sea cells with base count < nb:", ((cnt_cell_base < nb) & sea_targ).sum())
print("non-sea cells with base count == nb:", ((cnt_cell_base == nb) & ~sea_targ).sum())

c = np.load("work/clim.npz")
thr_s = c["thr_s"]; clm_s = c["clm_s"]
print("cells with NaN thr_s:", np.isnan(thr_s).any(axis=0).sum())
print("cells with NaN clm_s:", np.isnan(clm_s).any(axis=0).sum())
print("NaN-thr cells that are sea cells:", (np.isnan(thr_s).any(axis=0) & sea_targ).sum())
print("NaN-thr cells that are NOT sea cells:", (np.isnan(thr_s).any(axis=0) & ~sea_targ).sum())
# do NaN-thr cells coincide with cells having baseline gaps?
print("overlap NaNthr & (0 < basecnt < nb):", (np.isnan(thr_s).any(axis=0) & (cnt_cell_base > 0) & (cnt_cell_base < nb)).sum())
