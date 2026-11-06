import numpy as np, h5py
D='/data/icsa2027_data_20261101T090944Z/s1z'
p=f'{D}/sst_19920601.nc'
with h5py.File(p,'r') as f:
    full=f['analysed_sst'][0]
    sub=f['analysed_sst'][0,34:94,213:273]
    sub2=full[34:94,213:273]
print("full[40,40]:", full[40,40], " sub[6,6] (same cell):", sub[6,6], " full-slice[6,6]:", sub2[6,6])
print("finite full:", np.isfinite(full).mean(), " finite sub:", np.isfinite(sub).mean())
print("sub == full-slice:", np.array_equal(sub, sub2, equal_nan=True))
# read full field twice
with h5py.File(p,'r') as f:
    full2=f['analysed_sst'][0]
print("full stable across reads:", np.array_equal(full, full2, equal_nan=True))
print("nan count full:", np.isnan(full).sum(), "of", full.size)
# where are nans? bounding box
ys,xs=np.where(np.isnan(full))
print("nan rows range:", ys.min(), ys.max(), "nan cols range:", xs.min(), xs.max())
