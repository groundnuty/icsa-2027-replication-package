import h5py, numpy as np, time
f = h5py.File('/work/sst_s2.nc', 'r')
v = f['analysed_sst']
n = v.shape[0]
ref = np.ascontiguousarray(v[3652])  # 1992-01-01

t0 = time.time()
M = 300
counts = np.empty(M, dtype=np.int64)
for i in range(M):
    a = np.asarray(v[i])
    counts[i] = np.sum((a != ref) & (np.isfinite(a) | np.isfinite(ref)))
dt = (time.time()-t0)/M
print(f"per-chunk time: {dt*1000:.1f} ms -> full scan est {n*dt/60:.1f} min")
print("counts first 50:", counts[:50])
print("indices with diff>0:", np.where(counts>0)[0][:50])
f.close()
