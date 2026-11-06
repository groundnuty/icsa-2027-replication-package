import h5py, numpy as np, time
f = h5py.File('/work/sst_s2.nc', 'r')
v = f['analysed_sst']
n = v.shape[0]
t0=time.time()
res = np.zeros((n,4), dtype=np.float64)
for i in range(n):
    a = np.asarray(v[i]).ravel()
    fin = a[np.isfinite(a)]
    res[i,0] = fin.sum() if fin.size else 0.0
    res[i,1] = fin.mean() if fin.size else np.nan
    res[i,2] = fin.min() if fin.size else np.nan
    res[i,3] = fin.max() if fin.size else np.nan
    if i % 2000 == 0:
        print(i, f"elapsed {(time.time()-t0):.0f}s", flush=True)
print("done", time.time()-t0)
np.save('/work/slice_stats.npy', res)
# show rows where stats change
chg = np.where(~np.all(np.isclose(res[1:], res[:-1], rtol=0, atol=0), axis=1))[0]
print("n change points:", chg.size)
print(chg[:80])
f.close()
