import numpy as np, pandas as pd

z = np.load('/work/clim_thr.npz')
thr_s, clim_s, sea = z['thr_s'], z['clim_s'], z['sea']
sst_tgt = np.load('/work/sst_tgt.npy').astype(np.float64)

# locate NaNs on sea cells
fin_t = np.isfinite(thr_s)
fin_c = np.isfinite(clim_s)
bad_t = ~fin_t[:, sea]   # (367, n_sea)
bad_c = ~fin_c[:, sea]
print("non-finite thr on sea: doys", np.where(bad_t.any(axis=1))[0])
print("non-finite clim on sea: doys", np.where(bad_c.any(axis=1))[0])
for d in np.where(bad_t.any(axis=1))[0]:
    cells = np.where(~fin_t[d] & sea)
    print(f"  doy {d}: n bad cells {len(cells[0])}, raw thr[59,61] finite there?",
          bool(np.isfinite(z['thr'][59][cells]).all()), bool(np.isfinite(z['thr'][61][cells]).all()))
# check raw thr/clim on sea cells
print("raw thr finite on sea:", bool(np.isfinite(z['thr'][1:][:, sea]).all()))
print("raw clim finite on sea:", bool(np.isfinite(z['clim'][1:][:, sea]).all()))
# which raw doy is bad?
print("bad raw thr doys:", np.where(~np.isfinite(z['thr'][1:][:, sea]).all(axis=1))[0] + 1)
print("bad raw clim doys:", np.where(~np.isfinite(z['clim'][1:][:, sea]).all(axis=1))[0] + 1)
