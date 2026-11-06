
import xarray as xr, numpy as np
ds = xr.open_dataset('output/mhw_mask.nc')
m = ds.mhw.values  # (92, 60, 60)
colsum = m.sum(axis=0)  # (60, 60)
print("cells all-zero over time (should be 296 land cells):", int((colsum==0).sum()))
print("cells with any MHW:", int((colsum>0).sum()))
sst = np.load('/tmp/sst_tgt.npy').reshape(92,60,60)
land = ~np.isfinite(sst).all(axis=0)
print("land mask matches all-zero cells:", bool((land == (colsum==0)).all()))
