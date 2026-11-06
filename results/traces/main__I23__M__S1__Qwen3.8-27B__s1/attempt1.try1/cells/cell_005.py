import os, time, h5py, numpy as np
d = "/data/icsa2027_data_20261101T090944Z/s1z"
i0,i1,j0,j1 = 196,256,485,545
t0=time.time()
vals=[]
for s in ["19911227","19920101","20130601","20030105"]:
    with h5py.File(f"{d}/sst_{s}.nc","r") as f:
        vals.append(f["analysed_sst"][0, i0:i1, j0:j1][:].astype(np.float64))
t1=time.time()
print("4 files in", t1-t0, "s")
v=np.vstack(vals)
print(v.shape)
print("finite per row:", np.isfinite(v).sum(axis=1))
print("sample min/max:", np.nanmin(v), np.nanmax(v))
print("n cells finite in all 4:", np.all(np.isfinite(v),axis=0).sum())
